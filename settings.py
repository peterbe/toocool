PROJECT_TITLE = u"Too cool for me?"
DATABASE_NAME = "toocool"

COOKIE_SECRET = "92orTzK3XqaGUYdkL3gmUejIFuY37EQn92XsTo1v/Vi="
TWITTER_CONSUMER_KEY = None
TWITTER_CONSUMER_SECRET = None

REDIS_HOST = 'localhost'
REDIS_PORT = 6379

# complete this in your local_settings.py to get emails sent on errors
ADMIN_EMAILS = (
)

try:
    from local_settings import *
except ImportError:
    pass


assert TWITTER_CONSUMER_KEY
assert TWITTER_CONSUMER_SECRET
