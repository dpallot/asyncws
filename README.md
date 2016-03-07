# async-websockets

<h3>About</h3>

``asyncws`` is a library for developing websocket applications in Python 3.

It implements [RFC 6455](https://tools.ietf.org/html/rfc6455), passes the [Autobahn Testsuite](http://autobahn.ws/testsuite/) and supports SSL/TSL out of the box. Based on [PEP 3156](https://www.python.org/dev/peps/pep-3156/) and coroutines it makes it easy to write highly concurrent websocket based applications. 

<h3>Installation</h3>

To install the package: ``python3 setup.py install``

<h3>API Documentation</h3>
Refer to [API Documentation](https://async-websockets.readthedocs.org/) for more information. 

<h3>Example</h3>

Echo server:
`````python
import asyncio
import asyncws

@asyncio.coroutine
def echo(websocket):
     while True:
        frame = yield from websocket.recv()
        if frame is None:
            break
        yield from websocket.send(frame)

server = asyncws.start_server(echo, '127.0.0.1', 8000)
asyncio.get_event_loop().run_until_complete(server)
asyncio.get_event_loop().run_forever()
`````

Corresponding echo client:
`````python
 import asyncio
 import asyncws

 @asyncio.coroutine
 def echo():
     websocket = yield from asyncws.connect('ws://localhost:8000')
     while True:
         yield from websocket.send('hello')
         echo = yield from websocket.recv()
         if echo is None:
             break
         print (echo)

 asyncio.get_event_loop().run_until_complete(echo())
 asyncio.get_event_loop().close()
`````
<h3>SSL/TSL Example</h3>

The first step is to create the certificate and key files. A self-signed certificate can be created with a command like:

``openssl req -newkey rsa:2048 -nodes -keyout example.key -x509 -days 365 -out example.crt``

Create an SSLContext with the certificate and key just generated and then pass the context to start_server():

`````python
import asyncio
import asyncws
import ssl

@asyncio.coroutine
def echo(websocket):
    while True:
        frame = yield from websocket.recv()
        if frame is None:
            break
        yield from websocket.send(frame)

ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_context.check_hostname = False
ssl_context.load_cert_chain('example.crt', 'example.key')

server = asyncws.start_server(echo, '127.0.0.1', 8000, ssl = ssl_context)
asyncio.get_event_loop().run_until_complete(server)
asyncio.get_event_loop().run_forever()
`````

An SSLContext is needed to secure the client-side of the socket:

`````python
import asyncio
import asyncws
import ssl

@asyncio.coroutine
def echo():
    ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ssl_context.check_hostname = False
    ssl_context.load_verify_locations('example.crt')

    websocket = yield from asyncws.connect('wss://localhost:8000', ssl = ssl_context)
    while True:
        yield from websocket.send('hello')
        echo = yield from websocket.recv()
        if echo is None:
            break
        print (echo)

asyncio.get_event_loop().run_until_complete(echo())
asyncio.get_event_loop().close()
`````

Now you have a fully encrypted websocket connection!
