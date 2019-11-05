#!/usr/bin/env python

import os
import sys
import logging
import signal
import ssl
import tornado.ioloop
import tornado.web
import tornado.httpserver


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
logging.getLogger("OwlKurentoClient").setLevel(logging.CRITICAL)
logging.getLogger("examples.helloworld.handlers").setLevel(logging.INFO)
logging.getLogger("examples.one2one.handlers").setLevel(logging.DEBUG)

import examples.multires.handlers
import examples.rooms.handlers
import examples.loopback.handlers
import examples.helloworld.handlers
import examples.one2one.handlers
from examples import render_view


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        render_view(self, "index")

application = tornado.web.Application([
    (r"/", IndexHandler),
    (r"/helloworld", examples.helloworld.handlers.HelloWorldHandler),
    (r"/helloworldws", examples.helloworld.handlers.HelloWorldWSHandler),
    (r"/one2one", examples.one2one.handlers.One2OneHandler),
    (r"/one2onews", examples.one2one.handlers.One2OneWSHandler),
    (r"/loopback", examples.loopback.handlers.LoopbackHandler),
    (r"/multires", examples.multires.handlers.MultiResHandler),
    (r"/room", examples.rooms.handlers.RoomIndexHandler),
    (r"/room/(?P<room_id>\d*)", examples.rooms.handlers.RoomHandler),
    (r"/room/(?P<room_id>[^/]*)/subscribe/(?P<from_participant_id>[^/]*)/(?P<to_participant_id>[^/]*)",
        examples.rooms.handlers.SubscribeToParticipantHandler),
    (r'/static/(.*)', tornado.web.StaticFileHandler,
        {'path': os.path.join(os.path.dirname(__file__), "static")}),
], debug=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8090))
    application.listen(port)
    print("Webserver now listening on port %d" % port)

    # Add HTTPS Server
    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    ssl_context.load_cert_chain("/home/chance/git/moltres/defaultCertificate.pem")
    https_server = tornado.httpserver.HTTPServer(application, ssl_options=ssl_context)
    https_server.listen(443)

    ioloop = tornado.ioloop.IOLoop.instance()
    signal.signal(signal.SIGINT, lambda sig, frame: ioloop.stop())
    ioloop.start()
