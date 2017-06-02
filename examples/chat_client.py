import asyncio
import asyncws
import sys

@asyncio.coroutine
def stdin():
    reader = asyncio.StreamReader()
    yield from asyncio.get_event_loop().connect_read_pipe(
        lambda: asyncio.StreamReaderProtocol(reader), sys.stdin)
    return reader


@asyncio.coroutine
def chat_recv(websocket, send_task):
    while True:
        echo = yield from websocket.recv()
        if echo is None:
            break
        print(echo)
    send_task.cancel()

@asyncio.coroutine
def chat_send(websocket):
    reader = yield from stdin()
    print("Welcome, type some text!")
    while True:
        msg = yield from reader.readline()
        yield from websocket.send(
            msg.decode('utf-8').strip('\r\n'), True)


@asyncio.coroutine
def chat(websocket):
    send_task = asyncio.Task(chat_send(websocket))
    recv_task = asyncio.Task(chat_recv(websocket, send_task))
    return [recv_task, send_task]


loop = asyncio.get_event_loop()
websocket = loop.run_until_complete(
    asyncws.connect('ws://localhost:8000'))
try:
    chat_tasks = loop.run_until_complete(chat(websocket))
    loop.run_until_complete(asyncio.wait(chat_tasks))
except KeyboardInterrupt as e:
    loop.run_until_complete(websocket.close())
    loop.run_until_complete(websocket.wait_closed())
    for task in chat_tasks:
        task.cancel()
    loop.run_until_complete(asyncio.wait(chat_tasks))
finally:
    loop.close()
