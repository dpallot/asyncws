import asyncio
import asyncws

@asyncio.coroutine
def echo(websocket):
    while True:
        yield from websocket.send('hello')
        msg = yield from websocket.recv()
        if msg is None:
            break
        print(msg)


loop = asyncio.get_event_loop()
websocket = loop.run_until_complete(
    asyncws.connect('ws://localhost:8000'))
try:
    loop.run_until_complete(echo(websocket))
except KeyboardInterrupt as e:
    loop.run_until_complete(websocket.close())
    loop.run_until_complete(websocket.wait_closed())
finally:
    loop.close()
