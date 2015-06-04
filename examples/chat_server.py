import asyncio
import asyncws

clients = []
clients_lock = asyncio.Lock()

def chat(websocket):
    
    with (yield from clients_lock):
        clients.append(websocket)

    try:
        while True:
            frame = yield from websocket.recv()
            if frame is None:
                break

            client_copy = None
            with (yield from clients_lock):
                client_copy = list(clients)

            for client in client_copy:    
                if client is websocket:
                    continue
                yield from client.send(frame)
    finally:
        with (yield from clients_lock):
            clients.remove(websocket)

server = asyncws.start_server(chat, '127.0.0.1', 8000)
asyncio.get_event_loop().run_until_complete(server)
asyncio.get_event_loop().run_forever()