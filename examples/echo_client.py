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