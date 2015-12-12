import asyncio
import asyncws
import sys

@asyncio.coroutine
def stdin():
    reader = asyncio.StreamReader()
    yield from asyncio.get_event_loop().connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
    return reader

@asyncio.coroutine
def chat_recv(websocket):
    while True:
        echo = yield from websocket.recv()
        if echo is None:
            break
        print (echo)

@asyncio.coroutine
def chat_send(websocket):
    reader = yield from stdin()
    print ("Welcome, type some text!")
    while True:
        msg = yield from reader.readline()
        yield from websocket.send(msg.decode('utf-8').strip('\r\n'), True)

@asyncio.coroutine
def chat():
    websocket = yield from asyncws.connect('ws://localhost:8000')
    tasks = [chat_recv(websocket), chat_send(websocket)]
    yield from asyncio.wait(tasks)

asyncio.get_event_loop().run_until_complete(chat())
asyncio.get_event_loop().close()
