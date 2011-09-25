#!/usr/bin/env python
import os
import site

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
path = lambda *a: os.path.join(ROOT,*a)

site.addsitedir(path('.'))
site.addsitedir(path('vendor'))

import redis as redis_

def run():
    import settings
    from models import connection
    db = connection[settings.DATABASE_NAME]
    redis = redis_.client.Redis(settings.REDIS_HOST,
                               settings.REDIS_PORT)

    for username in redis.smembers('allusernames'):
        key = 'access_tokens:%s' % username
        access_token = redis.get(key)
        if access_token:
            user = db.User.find_one({'username': username})
            if not user:
                user = db.User()
                user['username'] = username
            user['access_token'] = access_token
            user.save()

if __name__ == '__main__':
    run()
