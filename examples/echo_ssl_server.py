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

loop = asyncio.get_event_loop()
loop.set_debug(True)
server = loop.run_until_complete(
    asyncws.start_server(echo, '127.0.0.1', 8000, ssl=ssl_context))
try:
    loop.run_forever()
except KeyboardInterrupt as e:
    server.close()
    loop.run_until_complete(server.wait_closed())
finally:
    loop.close()

