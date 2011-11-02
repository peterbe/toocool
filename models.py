import re
import datetime
from pymongo.objectid import ObjectId
from mongolite import Connection, Document



connection = Connection()

class BaseDocument(Document):
    skeleton = {
      'modify_date': datetime.datetime
    }

    default_values = {'modify_date': datetime.datetime.utcnow}

    def save(self, *args, **kwargs):
        if '_id' in self and kwargs.get('update_modify_date', True):
            m = datetime.datetime.utcnow()
            self['modify_date'] = m
        super(BaseDocument, self).save(*args, **kwargs)


@connection.register
class User(BaseDocument):
    __collection__ = 'users'
    skeleton = {
      'username': unicode,
      'access_token': dict,
      'modify_date': datetime.datetime
    }
    optional = {
      'user_id': int,
    }


@connection.register
class Tweeter(BaseDocument):
    __collection__ = 'tweeters'
    skeleton = {
      'user_id': int,
      'username': unicode,
      'name': unicode,
      'followers': int,
      'following': int,
      'ratio': float,
      'last_tweet_date': datetime.datetime,
    }
    optional = {
      'ratio_rank': int,
    }

    def set_ratio(self):
        self['ratio'] = 1.0 * self['followers'] / max(self['following'], 1)

    @staticmethod
    def find_by_username(db, username):
        tweeter = db.Tweeter.find_one({'username': username})
        if not tweeter:
            tweeter = db.Tweeter.find_one({'username': re.compile(re.escape(username), re.I)})
        return tweeter

    @staticmethod
    def update_tweeter(tweeter, user):
        if tweeter['name'] != user['name']:
            tweeter['name'] = user['name']

        if tweeter['username'] != user['screen_name']:
            tweeter['username'] = user['screen_name']

        if tweeter['followers'] != user['followers_count']:
            tweeter['followers'] = user['followers_count']

        if tweeter['following'] != user['friends_count']:
            tweeter['following'] = user['friends_count']

        def parse_status_date(dstr):
            dstr = re.sub('\+\d{1,4}', '', dstr)
            return datetime.datetime.strptime(
              dstr,
              '%a %b %d %H:%M:%S %Y'
            )
        last_tweet_date = None
        if 'status' in user:
            last_tweet_date = user['status']['created_at']
            last_tweet_date = parse_status_date(last_tweet_date)
            if tweeter['last_tweet_date'] != last_tweet_date:
                tweeter['last_tweet_date'] = last_tweet_date

        ratio_before = tweeter['ratio']
        tweeter.set_ratio()
        tweeter.save()



@connection.register
class Following(BaseDocument):
    __collection__ = 'following'
    skeleton = {
      'user': unicode,
      'follows': unicode,
      'following': bool,
    }
