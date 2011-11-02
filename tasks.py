import logging
import tornado.escape
import tornado.auth
import tornado.ioloop
from celery.task import task
from celery import conf
import settings
from models import Tweeter, connection



@task
def refresh_user_info(*args, **kwargs):
    try:
        _refresh_user_info(*args, **kwargs)
    except:
        logging.error("_refresh_user_info() failed", exc_info=True)
        if conf.ALWAYS_EAGER:
            raise

def _refresh_user_info(username, access_token):
    #from time import sleep; sleep(5)
    uu = UserUpdate()
    def cb(r, *args, **kwargs):
        try:
            uu.callback(username, r)
        finally:
            if not conf.ALWAYS_EAGER:
                tornado.ioloop.IOLoop.instance().stop()
    uu.twitter_request("/users/show", cb, access_token=access_token,
                       screen_name=username)
    if not conf.ALWAYS_EAGER:
        tornado.ioloop.IOLoop.instance().start()


class UserUpdate(tornado.auth.TwitterMixin):
    def __init__(self):
        self.settings = dict(
            twitter_consumer_key=settings.TWITTER_CONSUMER_KEY,
            twitter_consumer_secret=settings.TWITTER_CONSUMER_SECRET,
        )

    @property
    def db(self):
        return connection[settings.DATABASE_NAME]

    def require_setting(self, key, error):
        assert key in self.settings, "%s (%s)" % (error, key)

    def async_callback(self, func, callback):
        return callback

    def callback(self, username, response):
        result = tornado.escape.json_decode(response.body)
        tweeter = self.db.Tweeter.find_one({'user_id': result['id']})
        assert tweeter['username'].lower() == username.lower()
        Tweeter.update_tweeter(tweeter, result)
