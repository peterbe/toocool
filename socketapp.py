#!/usr/bin/env python
import os
import re
import here
import logging
from pprint import pprint
import tornado.escape
import redis.client
import tornado.options
from tornado.options import define, options
import settings

from tornadio2 import SocketConnection, TornadioRouter, SocketServer, event

define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=8888, help="run on the given port (default 8888)", type=int)


class LookupsConnection(SocketConnection):
    connected_clients = set()
    def on_open(self, request):
        #print "OPEN"
        for each in self.connected_clients:
            each.send({'message': "Someone connected!"})
        self.connected_clients.add(self)

    def on_message(self, message):
        logging.debug("RECEIVED: %r" % message)
        for client in self.connected_clients:
            if client != self:
                #print "CLIENT", repr(client)
                #print "\t", client.is_closed
                if client.is_closed:
                    print "DBG consider deleting", repr(client)
                else:
                    client.send({'message': message.upper()})

    def on_close(self):
        logging.debug("Closing client")
        if self in self.connected_clients:
            logging.debug("Removing %r" % self)
            self.connected_clients.remove(self)


def redis_listener():
    r = redis.Redis(settings.REDIS_HOST, settings.REDIS_PORT)
    ps = r.pubsub()
    ps.subscribe(['lookups'])
    for message in ps.listen():
        try:
            data = tornado.escape.json_decode(message['data'])
        except ValueError:
            data = message['data']

        #print "****MESSAGE"
        #pprint(data)
        #print "\t send this to", len(LookupsConnection.connected_clients), 'clients'
        to_send = {}
        for key, value in data.items():
            new_key = {
              'lookups:json': 'lookups_json',
              'lookups:jsonp': 'lookups_jsonp',
              'auths:total': 'auths',
              'lookups:usernames': 'lookups_usernames'
            }.get(key)
            if new_key is None:
                print "Skipping", repr(key)
                continue
            #print new_key, repr(value)
            to_send[new_key] = value

        for client in LookupsConnection.connected_clients:
            client.send(to_send)



def main():
    import threading
    t = threading.Thread(target=redis_listener)
    t.setDaemon(True)
    t.start()

    LookupsServer = TornadioRouter(LookupsConnection)
    # Fill your routes here
    routes = []
    # Extend list of routes with Tornadio2 URLs
    routes.extend(LookupsServer.urls)

    tornado.options.parse_command_line()
    if options.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    application = tornado.web.Application(routes,
      socket_io_port=options.port)
    try:
        SocketServer(application)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
