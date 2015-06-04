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