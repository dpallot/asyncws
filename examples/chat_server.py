import asyncio
import asyncws

clients = []
clients_lock = asyncio.Lock()

def chat(websocket):

    client_copy = None

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

server = asyncws.start_server(chat, '127.0.0.1', 8000)
asyncio.get_event_loop().run_until_complete(server)
asyncio.get_event_loop().run_forever()
