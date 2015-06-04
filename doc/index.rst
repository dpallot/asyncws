.. asyncws documentation master file, created by
   sphinx-quickstart on Tue Jun  2 23:11:02 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

asyncws - Asynchronous websockets for asyncio
=============================================

``asyncws`` is a library for developing websocket applications in Python 3. 
It implements `RFC 6455 <https://tools.ietf.org/html/rfc6455>`_, passes the `Autobahn Testsuite <http://autobahn.ws/testsuite/>`_ and supports SSL/TSL out of the box.

Based on `PEP 3156 <https://www.python.org/dev/peps/pep-3156/>`_ and coroutines it makes it easy to write highly concurrent websocket based applications. 

Echo server example::

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

Corresponding echo client example::

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


API Documentation

.. toctree::
   :maxdepth: 4

.. automodule:: asyncws
 
.. autoclass:: Websocket
    :members:

.. autofunction:: connect

.. autofunction:: start_server

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

