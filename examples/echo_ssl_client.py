import asyncio
import asyncws
import ssl

@asyncio.coroutine
def echo(websocket):
    while True:
        yield from websocket.send('hello')
        echo = yield from websocket.recv()
        if echo is None:
            break
        print(echo)


ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE
ssl_context.load_verify_locations('example.crt')

loop = asyncio.get_event_loop()
websocket = loop.run_until_complete(
    asyncws.connect('wss://localhost:8000', ssl=ssl_context))
try:
    loop.run_until_complete(echo(websocket))
except KeyboardInterrupt as e:
    loop.run_until_complete(websocket.close())
    loop.run_until_complete(websocket.wait_closed())
finally:
    loop.close()

