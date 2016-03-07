import asyncio
import base64
import hashlib
import codecs
import struct
import random
import urllib.parse
from io import BytesIO, StringIO
from http.client import HTTPResponse
from http.server import BaseHTTPRequestHandler

from .exceptions import *

__all__ = ['_WEBSOCKET_MAX_HEADER', '_WEBSOCKET_MAX_PAYLOAD', '_WEBSOCKET_HANDSHAKE_TIMEOUT',
            'Websocket', 'start_server', 'connect']

_REQUEST = (
    'GET %(path)s HTTP/1.1\r\n'
    'Upgrade: websocket\r\n'
    'Connection: Upgrade\r\n'
    'Host: %(host_port)s\r\n'
    'Origin: file://\r\n'
    'Sec-WebSocket-Key: %(key)s\r\n'
    'Sec-WebSocket-Version: 13\r\n\r\n'
)

_RESPONSE = (
    'HTTP/1.1 101 Switching Protocols\r\n'
    'Upgrade: websocket\r\n'
    'Connection: Upgrade\r\n'
    'Sec-WebSocket-Accept: %(accept_string)s\r\n\r\n'
)

_GUID_STRING = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

_STREAM = 0x0
_TEXT = 0x1
_BINARY = 0x2
_CLOSE = 0x8
_PING = 0x9
_PONG = 0xA

_WEBSOCKET_MAX_PAYLOAD = 33554432
_WEBSOCKET_MAX_HEADER = 65536
_WEBSOCKET_HANDSHAKE_TIMEOUT = 10

_VALID_STATUS_CODES = [1000, 1001, 1002, 1003, 1007, 1008, 1009, 1010, 1011, 3000, 3999, 4000, 4999]

class FakeSocket():
    def __init__(self, response_str):
        self._file = BytesIO(response_str)

    def makefile(self, *args, **kwargs):
        return self._file

class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request):
        self.rfile = BytesIO(request)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message

class Websocket:
    """
    Class that wraps the websocket protocol.

    :param writer: Access to ``get_extra_info()``. See `StreamWriter. \
        <https://docs.python.org/3.4/library/asyncio-stream.html#asyncio.StreamWriter>`_
    :param request: HTTP request that arrives at the server during handshaking. \
        See `BaseHTTPRequestHandler. <https://docs.python.org/3.4/library/http.server.html#http.server.BaseHTTPRequestHandler>`_ \
        Set to ``None`` if it's a client websocket.
    :param response: HTTP response that arrives at the client after handshaking is complete. \
        See `HTTPResponse. <https://docs.python.org/3.4/library/http.client.html#http.client.HTTPResponse>`_ \
        Set to ``None`` if it's a server websocket.
    """
    def __init__(self, reader, writer):
        self.writer = writer
        self._reader = reader
        self.response = None
        self.request = None
        self._closed = False
        self._mask = False
        self.status = 1000
        self.reason = ''

    @asyncio.coroutine
    def handshake(self):
        """
        This function allows server based websocket applications to initiate a handshake with a client endpoint.
        To initiate a manual handshake ``auto_handshake = False`` must be passed to ``start_server``::

            @asyncio.coroutine
            def echo(websocket):
                yield from websocket.handshake()
                while True:
                    frame = yield from websocket.recv()
                    if frame is None:
                        break
                    yield from websocket.send(frame)

            asyncws.start_server(echo, '127.0.0.1', 8000, auto_handshake = False)

        :raises Exception: When there is an error in the handshake.
        """
        request = yield from handshake_with_client(self._reader, self.writer)
        self.request = request

    @asyncio.coroutine
    def close(self, status = 1000, reason = ''):
        """
        Start the close handhake by sending a close frame to the websocket endpoint. \
            Once the endpoint responds with a corresponding close the underlying transport is closed.

        To force close the websocket without going through the close handshake call ``self.writer.close()``
        which will immediately tear down the underlying transport.

        :param status: See `Status Codes. <https://tools.ietf.org/html/rfc6455#section-7.4>`_
        :param reason: Why the websocket is being closed.
        :raises Exception: When there is an error sending data to the endpoint.
        """
        if self._closed is False:
            self._closed = True
            yield from send_close_frame(self.writer, status, reason, self._mask)

    @asyncio.coroutine
    def send(self, data, flush = False):
        """
        Send a data frame to websocket endpoint.

        :param data: If data is of type ``str`` then the data is sent as a text frame.
                     If data is of type ``byte`` then the data is sent as a binary frame.
        :param flush: When set to ``True`` then the send buffer is flushed immediately.
        :raises Exception: When there is an error sending data to the endpoint only if flush is set to ``True``.
        """
        payload = data
        opcode = _BINARY
        if isinstance(data, str):
            opcode = _TEXT
            payload = data.encode('utf-8')

        yield from send_frame(self.writer, False, opcode, payload, self._mask, flush)

    @asyncio.coroutine
    def send_fragment_start(self, data, flush = False):
        payload = data
        opcode = _BINARY
        if isinstance(data, str):
            opcode = _TEXT
            payload = data.encode('utf-8')

        yield from send_frame(self.writer, True, opcode, payload, self._mask, flush)

    @asyncio.coroutine
    def send_fragment(self, data, flush = False):
        payload = data
        if isinstance(data, str):
            payload = data.encode('utf-8')

        yield from send_frame(self.writer, True, _STREAM, payload, self._mask, flush)

    @asyncio.coroutine
    def send_fragment_end(self, data, flush = False):
        payload = data
        if isinstance(data, str):
            payload = data.encode('utf-8')

        yield from send_frame(self.writer, False, _STREAM, payload, self._mask, flush)

    @asyncio.coroutine
    def ping(self, data, flush = False):
        payload = data
        if isinstance(data, str):
            payload = data.encode('utf-8')

        yield from send_frame(self.writer, False, _PING, payload, self._mask, flush)

    @asyncio.coroutine
    def recv(self):
        """
        Recieve websocket frame from endpoint.

        This coroutine will block until a complete frame is ready.

        :return: Websocket text or data frame on success. \
            Returns ``None`` if the connection is closed or there is an error.
        """
        item = yield from recv_entire_frame(self)
        return item


@asyncio.coroutine
def recv_entire_frame(ws):

    try:
        _frag_start = False
        _frag_type = _BINARY
        _frag_buffer = None
        _frag_decoder = codecs.getincrementaldecoder('utf-8')()

        while True:
            fin, opcode, length, frame = yield from recv_frame(ws._reader)
            if opcode == _CLOSE:
                status = 1000
                reason = b''
                length = len(frame)

                if length == 0:
                    pass
                elif length >= 2:
                    status = struct.unpack_from('!H', frame[:2])[0]
                    reason = frame[2:]

                    if status not in _VALID_STATUS_CODES:
                        status = 1002

                    if len(reason) > 0:
                        try:
                            reason = reason.decode('utf-8')
                        except:
                            status = 1002
                else:
                    status = 1002

                yield from ws.close(status, reason)
                raise ClosedException(status, reason)

            if fin == 0:
                # fragmentation start
                if opcode != _STREAM:
                    if opcode == _PING or opcode == _PONG or opcode == _CLOSE:
                        raise ClosedException(1002, 'control messages can not be fragmented')

                    _frag_type = opcode
                    _frag_start = True
                    _frag_decoder.reset()

                    if _frag_type == _TEXT:
                        _frag_buffer = []
                        utf_str = _frag_decoder.decode(frame, final = False)
                        if utf_str:
                            _frag_buffer.append(utf_str)
                    else:
                        _frag_buffer = bytearray()
                        _frag_buffer.extend(frame)

                    if len(_frag_buffer) > _WEBSOCKET_MAX_PAYLOAD:
                        raise ClosedException(1009, 'payload too large')
                else:
                    # got a fragment packet without a start
                    if _frag_start is False:
                        raise ClosedException(1002, 'fragmentation protocol error')

                    if _frag_type == _TEXT:
                        utf_str = _frag_decoder.decode(frame, final = False)
                        if utf_str:
                            _frag_buffer.append(utf_str)
                    else:
                        _frag_buffer.extend(frame)

                    if len(_frag_buffer) > _WEBSOCKET_MAX_PAYLOAD:
                        raise ClosedException(1009, 'payload too large')
            else:

                if opcode == _STREAM:
                    if _frag_start is False:
                        raise ClosedException(1002, 'fragmentation protocol error')

                    if _frag_type == _TEXT:
                        utf_str = _frag_decoder.decode(frame, final = True)
                        _frag_buffer.append(utf_str)
                        _frag_buffer = ''.join(_frag_buffer)
                    else:
                        _frag_buffer.extend(frame)
                        _frag_buffer = bytes(_frag_buffer)

                    if len(_frag_buffer) > _WEBSOCKET_MAX_PAYLOAD:
                        raise ClosedException(1009, 'payload too large')

                    return _frag_buffer

                elif opcode == _PING:
                    yield from send_frame(ws.writer, False, _PONG, frame)

                elif opcode == _PONG:
                    continue

                else:
                    if _frag_start is True:
                        raise ClosedException(1002, 'fragmentation protocol error')

                    if opcode == _TEXT:
                        try:
                            frame = frame.decode('utf-8')
                        except Exception as exp:
                            raise ClosedException(1002, 'invalid utf-8 payload')

                    return frame

    except BaseException as exp:
        ws.writer.close()

        status = 1002
        reason = b''
        if isinstance(exp, ClosedException):
            status = exp.status
            reason = exp.reason
        else:
            reason = str(exp)

        ws.status = status
        ws.reason = reason

        return None

@asyncio.coroutine
def connect(wsurl, *, loop = None, limit = None, **kwds):
    """
    Connect to a websocket server. Connect will automatically carry out a websocket handshake.

    :param wsurl: Websocket uri. See `RFC6455 URIs. <https://tools.ietf.org/html/rfc6455#section-3>`_
    :param kwargs: See `open_connection. \
        <https://docs.python.org/3.4/library/asyncio-stream.html#asyncio.open_connection>`_
    :return: :class:`Websocket` object on success.
    :raises Exception: When there is an error during connection or handshake.
    """
    writer = None
    try:
        url = urllib.parse.urlparse(wsurl)

        port = 80
        if url.port:
            port = url.port

        use_ssl = False
        if url.scheme.startswith('wss://'):
            use_ssl = True
            if not url.port:
                port = 443

        reader, writer = yield from asyncio.open_connection(host = url.hostname, port = port, loop = loop, **kwds)
        response = yield from handshake_with_server(reader, writer, url)
        websocket = Websocket(reader, writer)
        websocket._mask = True
        websocket.reponse = response
        return websocket

    except BaseException as exp:
        if writer:
            writer.close()
        raise exp

@asyncio.coroutine
def start_server(func, host = None, port = None, *, loop = None, limit = None, auto_handshake = True, **kwds):
    """
    Start a websocket server, with a callback for each client connected.

    :param func: Called with a :class:`Websocket` parameter when a client connects and handshake is successful.
    :param auto_handshake: The handshake with a client occurs automatically by default. The only way to handle the handshake manually \
        is to set ``auto_handshake`` to ``False``. This means that the server application must \
        call :meth:`~asyncws.Websocket.handshake` on the websocket after it is passed to ``func``.
    :param kwags: See `start_server <https://docs.python.org/3.4/library/asyncio-stream.html#asyncio.start_server>`_
    :return: The return value is the same as `start_server <https://docs.python.org/3.4/library/asyncio-stream.html#asyncio.start_server>`_
    """
    server = yield from asyncio.start_server(lambda r, w: handle_server_websocket(r, w, func, auto_handshake), host, port, **kwds)
    return server

@asyncio.coroutine
def handle_server_websocket(reader, writer, func, auto_handshake):
    try:
        websocket = Websocket(reader, writer)
        if auto_handshake:
            request = yield from asyncio.wait_for(handshake_with_client(reader, writer), timeout = _WEBSOCKET_HANDSHAKE_TIMEOUT)
            websocket.request = request
        yield from func(websocket)
    except BaseException as exp:
        pass
    finally:
        writer.close()


@asyncio.coroutine
def handshake_with_server(reader, writer, parsed_url):

    try:
        rand = bytes(random.getrandbits(8) for _ in range(16))
        key = base64.b64encode(rand).decode()

        values = ''
        if parsed_url.query:
            values = '?' + parsed_url.query

        handshake = _REQUEST % {'path': parsed_url.path + values, 'host_port': parsed_url.netloc, 'key': key}

        writer.write(handshake.encode('utf-8'))
        yield from writer.drain()

        header_buffer = bytearray()
        while True:
            header = yield from reader.readline()
            if len(header) == 0:
                raise ProtocolError('no data from endpoint')

            header_buffer.extend(header)
            if len(header_buffer) > _WEBSOCKET_MAX_HEADER:
                raise ProtocolError('header too large')

            if header in b'\r\n':
                break

        response = HTTPResponse(FakeSocket(header_buffer))
        response.begin()

        accept_key = response.getheader('sec-websocket-accept')
        if key is None:
            raise ProtocolError('Sec-WebSocket-Accept does not exist')

        digested_key = base64.b64encode(hashlib.sha1((key + _GUID_STRING).encode('utf-8')).digest())
        if accept_key.encode() != digested_key:
            raise ProtocolError('Sec-WebSocket-Accept key does not match')

        return response

    except asyncio.CancelledError:
        writer.close()


@asyncio.coroutine
def handshake_with_client(reader, writer):
    try:
        header_buffer = bytearray()
        while True:
            header = yield from reader.readline()
            if len(header) == 0:
                raise ClosedException(1002, 'no data from endpoint')

            header_buffer.extend(header)
            if len(header_buffer) > _WEBSOCKET_MAX_HEADER:
                raise ClosedException(1009, 'header too large')

            if header in b'\r\n':
                break

        request = HTTPRequest(header_buffer)
        key = request.headers['sec-websocket-key']
        if key is None:
            raise ClosedException(1002, 'Sec-WebSocket-Key does not exist')

        digest = base64.b64encode(hashlib.sha1((key + _GUID_STRING).encode('utf-8')).digest())
        handshake = _RESPONSE % { 'accept_string':  digest.decode('utf-8') }
        writer.write(handshake.encode('utf-8'))
        yield from writer.drain()
        return request

    except asyncio.CancelledError as excp:
        response = 'HTTP/1.1 400 Bad Request\r\n\r\n' + str(excp)
        writer.write(response.encode('utf-8'))
        writer.close()

    except BaseException as exp:
        response = 'HTTP/1.1 400 Bad Request\r\n\r\n' + str(exp)
        writer.write(response.encode('utf-8'))
        writer.close()

        if not isinstance(exp, ClosedException):
            raise ClosedException(1002, str(exp))

        raise exp

@asyncio.coroutine
def send_close_frame(writer, status = 1000, reason = '', mask = False):
    close_msg = bytearray()
    close_msg.extend(struct.pack("!H", status))
    if isinstance(reason, str):
        close_msg.extend(reason.encode('utf-8'))
    else:
        close_msg.extend(reason)

    yield from send_frame(writer, False, _CLOSE, close_msg, mask, True)

@asyncio.coroutine
def send_frame(writer, fin, opcode, data, mask = False, flush = False):

    header = bytearray()
    b1 = 0
    b2 = 0

    if fin is False:
        b1 |= 0x80

    b1 |= opcode
    header.append(b1)

    if mask:
        b2 |= 0x80

    length = len(data)
    if length <= 125:
        b2 |= length
        header.append(b2)
    elif length >= 126 and length <= 65535:
        b2 |= 126
        header.append(b2)
        header.extend(struct.pack("!H", length))
    else:
        b2 |= 127
        header.append(b2)
        header.extend(struct.pack("!Q", length))

    writer.write(header)

    if mask:
        mask_bits = struct.pack('!I', random.getrandbits(32))
        writer.write(mask_bits)
        data = bytes(b ^ mask_bits[i % 4] for i, b in enumerate(data))

    if length > 0:
        writer.write(data)

    if flush:
        yield from writer.drain()

@asyncio.coroutine
def recv_frame(reader):

    h1, h2 = yield from reader.readexactly(2)

    fin = h1 & 0x80
    rsv = h1 & 0x70
    opcode = h1 & 0x0F
    mask = h2 & 0x80
    length = h2 & 0x7F

    # rsv must be 0 if not then close immediately
    if rsv != 0:
        raise ClosedException(1002, 'RSV bit must be 0')

    if opcode == _CLOSE:
        pass
    elif opcode == _STREAM:
        pass
    elif opcode == _TEXT:
        pass
    elif opcode == _BINARY:
        pass
    elif opcode == _PONG or opcode == _PING:
        if length > 125:
            raise ClosedException(1002, 'control frame length can not be > 125')
    else:
        # unknown or reserved opcode so just close
        raise ClosedException(1002, 'unknown opcode')

    # byte
    if length <= 125:
        pass
    # short
    elif length == 126:
        short_len = yield from reader.readexactly(2)
        length = struct.unpack_from('!H', short_len)[0]
    #long
    elif length == 127:
        long_len = yield from reader.readexactly(8)
        length = struct.unpack_from('!Q', long_len)[0]
    else:
        raise ClosedException(1002, 'unknown payload length')

    if length > _WEBSOCKET_MAX_PAYLOAD:
        raise ClosedException(1009, 'payload too large')

    if mask == 128:
        mask = yield from reader.readexactly(4)
    else:
        mask = None

    payload = b''
    if length > 0:
        payload = yield from reader.readexactly(length)
        if mask:
            mask_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            payload = mask_payload

    return bool(fin), opcode, length, payload
