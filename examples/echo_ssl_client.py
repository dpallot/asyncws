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
