# async-websockets

``asyncws`` is a library for developing websocket applications in Python 3. 
It implements [RFC 6455](https://tools.ietf.org/html/rfc6455), passes the [Autobahn Testsuite](http://autobahn.ws/testsuite/) and supports SSL/TSL out of the box.

Based on [PEP 3156](https://www.python.org/dev/peps/pep-3156/) and coroutines it makes it easy to write highly concurrent websocket based applications. 

Echo server example:
`````python

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
`````

Corresponding echo client example::
`````python
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
`````
