import site, os.path as op
ROOT = op.abspath(op.dirname(__file__))
path = lambda *a: op.join(ROOT, *a)
site.addsitedir(path('vendor'))

PROJECT_TITLE = u"Too cool for me?"
DATABASE_NAME = "toocool"

COOKIE_SECRET = "92orTzK3XqaGUYdkL3gmUejIFuY37EQn92XsTo1v/Vi="
TWITTER_CONSUMER_KEY = None
TWITTER_CONSUMER_SECRET = None

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

DATABASE_NAME = 'toocool'

try:
    from local_settings import *
except ImportError:
    pass


assert TWITTER_CONSUMER_KEY
assert TWITTER_CONSUMER_SECRET
