from pprint import pprint
import tornado.auth
import tornado.web
from tornado.web import HTTPError
from utils.routes import route
from tornado.escape import json_decode, json_encode
import settings

class BaseHandler(tornado.web.RequestHandler):

    def write_json(self, struct, javascript=False):
        if javascript:
            self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        else:
            self.set_header("Content-Type", "application/json; charset=UTF-8")
        #print "OUTPUT"
        #pprint(struct)

        self.write(tornado.escape.json_encode(struct))

    def write_jsonp(self, callback, struct):
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.write('%s(%s)' % (callback, tornado.escape.json_encode(struct)))

    def get_current_user(self):
        username = self.get_secure_cookie('user')
        if username:
            return unicode(username, 'utf8')

    @property
    def redis(self):
        return self.application.redis


@route('/')
class HomeHandler(BaseHandler):

    def get(self):
        options = {}
        user = self.get_current_user()
        if user:
            url = '/static/bookmarklet.js'
            url = '%s://%s%s' % (self.request.protocol,
                                 self.request.host,
                                 url)
            options['full_bookmarklet_url'] = url

        options['user'] = user
        self.render('home.html', **options)


@route('/json')
class FollowsHandler(BaseHandler, tornado.auth.TwitterMixin):

    @tornado.web.asynchronous
    def get(self):
        if (self.get_argument('username', None) and
            not self.get_argument('usernames', None)):
            usernames = self.get_arguments('username')
        else:
            usernames = self.get_arguments('usernames')
        if isinstance(usernames, basestring):
            usernames = [usernames]
        elif (isinstance(usernames, list)
              and len(usernames) == 1
              and ',' in usernames[0]):
            usernames = [x.strip() for x in
                         usernames[0].split(',')
                         if x.strip()]
        # make sure it's a unique list
        usernames = set(usernames)

        this_username = self.get_current_user()
        you = self.get_argument('you', None)  # optional
        if you:
            if this_username != you:
                self.write_json({
                  'ERROR': "Logged in on %s as '%s'" % this_username
                })
                return
            if you in usernames:
                usernames.remove(you)
        access_token = self.redis.get('username:%s' % this_username)
        if access_token:
            access_token = json_decode(access_token)
        if not access_token:
            self.write_json({
              'ERROR': ('Not authorized with Twitter for %s' %
                        self.request.host)
            })
            return
        #print "USERNAMES"
        #print usernames
        #print

        results = {}
        # pick some up already from the cache
        _drop = set()
        for username in usernames:
            key = 'follows:%s:%s' % (this_username, username)
            value = self.redis.get(key)
            if value is not None:
                #print repr(username)
                #print "\t", repr(value)
                results[username] = bool(int(value))
                _drop.add(username)
        usernames -= _drop

        if len(usernames) == 1:
            username = usernames[0]
            # See https://dev.twitter.com/docs/api/1/get/friendships/show
            self.twitter_request(
                "/friendships/show",
                source_screen_name=this_username,
                target_screen_name=username,
                access_token=access_token,
                callback=self.async_callback(
                  lambda x: self._on_show(x, this_username, username, results)
                ),
                )
        elif usernames:
            #print "ACCESS_TOKEN"
            #print access_token
            # See https://dev.twitter.com/docs/api/1/get/friendships/lookup
            self.twitter_request(
                "/friendships/lookup",
                screen_name=','.join(usernames),
                access_token=access_token,
                callback=self.async_callback(
                  lambda x: self._on_lookup(x, this_username, results)
                ),
            )
        else:
            # all usernames were lookup'able by cache
            self.write_json(results)
            self.finish()


    def _on_lookup(self, result, this_username, data):
        #print "RESULT"
        #pprint(result)
        for each in result:
            if 'followed_by' in each['connections']:
                data[each['screen_name']] = True
            else:
                data[each['screen_name']] = False
            key = 'follows:%s:%s' % (this_username, each['screen_name'])
            self.redis.setex(key, int(data[each['screen_name']]), 60)

        self.write_json(data)
        self.finish()

    def _on_show(self, result, this_username, username):
        #print "RESULT"
        #pprint(result)
        target_follows = None
        if result and 'relationship' in result:
            target_follows = result['relationship']['target']['following']
        key = 'follows:%s:%s' % (this_username, username)
        self.redis.setex(key, int(bool(target_follows)), 60)
        self.write_json({username: target_follows})
        self.finish()


class BaseAuthHandler(BaseHandler):

    def get_next_url(self):
        return '/'

@route('/auth/twitter/', name='auth_twitter')
class TwitterAuthHandler(BaseAuthHandler, tornado.auth.TwitterMixin):

    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("oauth_token", None):
            self.get_authenticated_user(self.async_callback(self._on_auth))
            return
        self.authenticate_redirect()

    def _on_auth(self, user_struct):
        if not user_struct:
            raise HTTPError(500, "Twitter auth failed")
        username = user_struct.get('username')
        #first_name = user_struct.get('first_name', user_struct.get('name'))
        #last_name = user_struct.get('last_name')
        #email = user_struct.get('email')
        access_token = user_struct['access_token']
        self.redis.set('username:%s' % username, json_encode(access_token))
        #profile_image_url = user_struct.get('profile_image_url', None)
        self.set_secure_cookie("user", username.encode('utf8'), expires_days=30)
        self.redirect('/')

@route(r'/auth/logout/', name='logout')
class AuthLogoutHandler(BaseAuthHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect(self.get_next_url())
