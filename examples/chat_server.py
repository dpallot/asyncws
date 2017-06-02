import asyncio
import asyncws

clients = []
clients_lock = asyncio.Lock()

def chat(websocket):
    with (yield from clients_lock):
        client_copy = list(clients)
        clients.append(websocket)

    peer = str(websocket.writer.get_extra_info('peername'))

    for client in client_copy:
        yield from client.send("Connected %s" % peer)

    try:
        while True:
            frame = yield from websocket.recv()
            if frame is None:
                break

            with (yield from clients_lock):
                client_copy = list(clients)

            text = "%s> %s" % (peer, str(frame))

            for client in client_copy:
                if client is websocket:
                    continue

                yield from client.send(text)
    finally:
        with (yield from clients_lock):
            clients.remove(websocket)
            client_copy = list(clients)

        for client in client_copy:
            yield from client.send("Disconnected %s" % peer)


loop = asyncio.get_event_loop()
server = loop.run_until_complete(
    asyncws.start_server(chat, '127.0.0.1', 8000))
try:
    loop.run_forever()
except KeyboardInterrupt as e:
    server.close()
    loop.run_until_complete(server.wait_closed())
finally:
    loop.close()
