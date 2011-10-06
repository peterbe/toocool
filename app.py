#!/usr/bin/env python
import os
import here
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import redis.client
from tornado.options import define, options
from tornado_utils.routes import route
import handlers
import settings


define("debug", default=False, help="run in debug mode", type=bool)
define("database_name", default=settings.DATABASE_NAME, help="db name")
define("port", default=8000, help="run on the given port", type=int)


class Application(tornado.web.Application):
    def __init__(self, database_name=None):
        routed_handlers = route.get_routes()
        app_settings = dict(
            title=settings.PROJECT_TITLE,
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            cookie_secret=settings.COOKIE_SECRET,
            debug=options.debug,
            twitter_consumer_key=settings.TWITTER_CONSUMER_KEY,
            twitter_consumer_secret=settings.TWITTER_CONSUMER_SECRET,
        )
        super(Application, self).__init__(routed_handlers, **app_settings)

        self.redis = redis.client.Redis(settings.REDIS_HOST,
                                        settings.REDIS_PORT)

        from models import connection
        self.db = connection[settings.DATABASE_NAME]



def main():  # pragma: no cover
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    print "Starting tornado on port", options.port
    http_server.listen(options.port)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
