import asyncio
import asyncws

@asyncio.coroutine
def echo(websocket):
    while True:
        frame = yield from websocket.recv()
        if frame is None:
            break
        yield from websocket.send(frame)


loop = asyncio.get_event_loop()
server = loop.run_until_complete(
    asyncws.start_server(echo, '127.0.0.1', 8000))
try:
    loop.run_forever()
except KeyboardInterrupt as e:
    server.close()
    loop.run_until_complete(server.wait_closed())
finally:
    loop.close()
