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
        self.write(tornado.escape.json_encode(struct))

    def write_jsonp(self, callback, struct):
        self.set_header("Content-Type", "text/javascript; charset=UTF-8")
        self.write('%s(%s)' % (callback, tornado.escape.json_encode(struct)))

    def get_current_user(self):
        return unicode(self.get_secure_cookie('user'), 'utf8')

    @property
    def redis(self):
        return self.application.redis


@route('/followsme')
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

        this_username = self.get_current_user()
        access_token = self.redis.get('username:%s' % this_username)
        if access_token:
            access_token = json_decode(access_token)

        if len(usernames) == 1:
            username = usernames[0]
            # See https://dev.twitter.com/docs/api/1/get/friendships/show
            self.twitter_request(
                "/friendships/show",
                source_screen_name=this_username,
                target_screen_name=username,
                access_token=access_token,
                callback=self.async_callback(
                  lambda x: self._on_show(x, this_username, username)
                ),
                )
        else:
            # See https://dev.twitter.com/docs/api/1/get/friendships/lookup
            self.twitter_request(
                "/friendships/lookup",
                screen_name=','.join(usernames),
                access_token=access_token,
                callback=self.async_callback(
                  lambda x: self._on_lookup(x, this_username)
                ),
            )

    def _on_lookup(self, result, this_username):
        #print "RESULT"
        #pprint(result)
        data = {}
        for each in result:
            if 'followed_by' in each['connections']:
                data[each['screen_name']] = True
            else:
                data[each['screen_name']] = False
        self.write_json(data)
        self.finish()

    def _on_show(self, result, this_username, username):
        #print "RESULT"
        #pprint(result)
        target_follows = None
        if result and 'relationship' in result:
            target_follows = result['relationship']['target']['following']
        #self.redis.set('follows
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
        self.set_secure_cookie("user", username.encode('utf8'), expires_days=100)
        self.redirect('/')

@route(r'/auth/logout/', name='logout')
class AuthLogoutHandler(BaseAuthHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect(self.get_next_url())
