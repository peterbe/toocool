import logging
from pprint import pprint, pformat
import tornado.auth
import tornado.web
from tornado.web import HTTPError
from tornado_utils.routes import route
#from tornado_utils.decorators import login_required
from tornado.escape import json_decode, json_encode
#import settings


class BaseHandler(tornado.web.RequestHandler):

    def write_json(self, struct, javascript=False):
        self.set_header("Content-Type", "application/json; charset=UTF-8")
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
        options = {
          'page_title': 'Too Cool for Me?',
        }
        user = self.get_current_user()
        if user:
            url = '/static/bookmarklet.js'
            url = '%s://%s%s' % (self.request.protocol,
                                 self.request.host,
                                 url)
            options['full_bookmarklet_url'] = url

        options['user'] = user
        self.render('home.html', **options)


@route('/json(p)?')
class FollowsHandler(BaseHandler, tornado.auth.TwitterMixin):

    @tornado.web.asynchronous
    def get(self, jsonp=False):

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
        if jsonp:
            self.jsonp = self.get_argument('callback', 'callback')
        else:
            self.jsonp = False

        #print "USERNAMES"
        #print usernames

        # All of this is commented out until I can figure out why cookie
        # headers aren't sent from bookmarklet's AJAX code
        this_username = self.get_argument('you', self.get_current_user())
#        this_username = self.get_current_user()
#        #print "THIS_USERNAME", repr(this_username)
#        you = self.get_argument('you', None)  # optional
#        #print "YOU", repr(you)
#        if you:
#            print "THIS_USERNAME", repr(this_username)
#            if this_username != you:
#                self.write_json({
#                  'ERROR': "Logged in on %s as '%s'" % this_username
#                })
#                return
#            if you in usernames:
#                usernames.remove(you)
        access_token = self.redis.get('username:%s' % this_username)
        print "access_token", access_token
        if access_token:
            access_token = json_decode(access_token)
        if not access_token:
            self.write_json({
              'ERROR': ('Not authorized with Twitter for %s' %
                        self.request.host)
            })
            self.finish()
            return
        print "USERNAMES"
        pprint(usernames)
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
            username = list(usernames)[0]
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
            print "ACCESS_TOKEN"
            print access_token
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
            if self.jsonp:
                self.write_jsonp(self.jsonp, results)
            else:
                self.write_json(results)
            print "RETURNING"
            pprint(results)
            self.finish()

    def _on_lookup(self, result, this_username, data):
        print "RESULT"
        pprint(result)
        for each in result:
            if 'followed_by' in each['connections']:
                data[each['screen_name']] = True
            else:
                data[each['screen_name']] = False
            key = 'follows:%s:%s' % (this_username, each['screen_name'])
            self.redis.setex(key, int(data[each['screen_name']]), 60)

        if self.jsonp:
            self.write_jsonp(self.jsonp, data)
        else:
            self.write_json(data)
        print "RETURNING"
        pprint(data)
        self.finish()

    def _on_show(self, result, this_username, username, data):
        #print "RESULT"
        #pprint(result)
        target_follows = None
        if result and 'relationship' in result:
            target_follows = result['relationship']['target']['following']
        key = 'follows:%s:%s' % (this_username, username)
        if target_follows is not None:
            self.redis.setex(key, int(bool(target_follows)), 60)
        data[username] = target_follows
        if self.jsonp:
            self.write_jsonp(self.jsonp, data)
        else:
            self.write_json(data)
        print "RETURNING"
        pprint(data)
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
        self.redis.rpush('usernames', username)
        #first_name = user_struct.get('first_name', user_struct.get('name'))
        #last_name = user_struct.get('last_name')
        #email = user_struct.get('email')
        access_token = user_struct['access_token']
        assert access_token
        self.redis.set('username:%s' % username, json_encode(access_token))
        #profile_image_url = user_struct.get('profile_image_url', None)
        self.set_secure_cookie("user",
                               username.encode('utf8'),
                               expires_days=30, path='/')
        self.redirect('/')


@route(r'/auth/logout/', name='logout')
class AuthLogoutHandler(BaseAuthHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect(self.get_next_url())


@route(r'/test', name='test')
class TestServiceHandler(BaseHandler):

    def get(self):
        options = {}
        user = self.get_current_user()
        if not user:
            self.redirect('/auth/twitter/')
            return
        options['user'] = user
        options['page_title'] = "Test the service"
        self.render('test.html', **options)


@route('/following/(\w+)')
class FollowingHandler(BaseHandler, tornado.auth.TwitterMixin):

    @tornado.web.asynchronous
    def get(self, username):
        options = {'username': username}
        this_username = self.get_current_user()
        if not this_username:
            self.redirect('auth_twitter')
            return
        options['this_username'] = this_username
        options['follows'] = None
        key = 'follows:%s:%s' % (this_username, username)
        value = self.redis.get(key)
        if value is None:
            access_token = self.redis.get('username:%s' % this_username)
            access_token = json_decode(access_token)
            self.twitter_request(
              "/friendships/show",
              source_screen_name=this_username,
              target_screen_name=username,
              access_token=access_token,
              callback=self.async_callback(
                lambda x: self._on_friendship(x, key, options)
              ),
            )
        else:
            self._on_friendship(bool(int(value)), None, options)
            #options['follows'] = bool(int(value))
            #self._fetch_info(options)

    def _on_friendship(self, result, key, options):
        if isinstance(result, bool):
            value = result
        else:
            logging.info("Result (%r): %r" % (key, result))
            if result and 'relationship' in result:
                value = result['relationship']['target']['following']
                if key and value is not None:
                    self.redis.setex(key, int(bool(value)), 60)
        options['follows'] = value
        self._fetch_info(options)

    def _fetch_info(self, options, username=None):
        if username is None:
            username = options['username']
        key = 'info:%s' % username
        value = self.redis.get(key)

        if value is None:
            access_token = self.redis.get('username:%s' %
                                          options['this_username'])
            access_token = json_decode(access_token)
            self.twitter_request(
              "/users/show",
              screen_name=username,
              access_token=access_token,
              callback=self.async_callback(
                lambda x: self._on_info(x, key, options)
              ),
            )
        else:
            self._on_info(json_decode(value), None, options)
            #value = json_decode(value)
            #options['info'] = value
            #pprint(value)
            #self._render(options)

    def _on_info(self, result, key, options):
        if isinstance(result, basestring):
            result = json_decode(result)
        if key:
            assert result
            self.redis.setex(key, json_encode(result), 60 * 60)
        if 'info' not in options:
            options['info'] = {options['username']: result}
            self._fetch_info(options, username=options['this_username'])
        else:
            options['info'][options['this_username']] = result
            self._render(options)

    def _render(self, options):
        if options['follows']:
            page_title = '%s follows you'
        else:
            page_title = '%s is too cool for me'
        options['page_title'] = page_title % options['username']
        #options['info_print'] = pformat(options['info'])
        #_followers = options['info']['followers_count']
        #_following = options['info']['friends_count']
        #options['ratios'][options['username']] =
        self._set_ratio(options, 'username')
        self._set_ratio(options, 'this_username')
        self.render('following.html', **options)

    def _set_ratio(self, options, key):
        try:
            value = options[key]
            followers = options['info'][value]['followers_count']
            following = options['info'][value]['friends_count']
            ratio = 1.0 * followers / following
            options['info'][value]['ratio'] = '%.1f' % ratio
            self.redis.sadd('allusernames', value)
            key = 'ratios'
            self.redis.zadd(key, **{value: ratio})
            _usernames = self.redis.zrange(key, 0, -1, withscores=False)
            _usernames.reverse()
            options['info'][value]['rank'] = _usernames.index(value)

        except:
            logging.error("KEY=%r, VALUE=%r, options['info']=%s" %
                          (key, value, pformat(options['info'])))
            raise


@route(r'/coolest')
class CoolestHandler(BaseHandler):

    def get(self):
        options = {}
        user = self.get_current_user()
        key = 'ratios'
        ratios = self.redis.zrange(key, 0, -1, withscores=True)
        ratios.reverse()
        options['ratios'] = ratios
        options['user'] = user
        options['page_title'] = \
          "Coolest in the world! ...on Twitter ...using this site"
        self.render('coolest.html', **options)
