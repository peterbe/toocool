import here  # so that the vendor lib is available later

# http://docs.celeryproject.org/en/latest/tutorials/otherqueues.html#redis
BROKER_TRANSPORT = "redis"

import settings
BROKER_HOST = settings.REDIS_HOST
BROKER_PORT = settings.REDIS_PORT
BROKER_VHOST = "0"         # Maps to database number.

CELERY_IGNORE_RESULT = True

CELERY_IMPORTS = ("tasks", )

import os
CELERY_ALWAYS_EAGER = bool(os.environ.get('ALWAYS_EAGER', False))
