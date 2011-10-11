import json
from urllib import urlencode
from .base import BaseHTTPTestCase
from handlers import TwitterAuthHandler, FollowsHandler, FollowingHandler

class HandlersTestCase(BaseHTTPTestCase):

    def setUp(self):
        super(HandlersTestCase, self).setUp()

        TwitterAuthHandler.authenticate_redirect = \
          twitter_authenticate_redirect

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.code, 200)
        self.assertTrue('Login with' in response.body)

    def test_twitter_login(self):
        assert not self.db.User.find_one({'username': 'peterbe'})
        TwitterAuthHandler.get_authenticated_user = \
          twitter_get_authenticated_user
        url = self.reverse_url('auth_twitter')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('twitter.com' in response.headers['location'])

        response = self.client.get(url, {'oauth_token':'xxx'})
        self.assertEqual(response.code, 302)

        user = self.db.User.find_one({'username': 'peterbe'})
        self.assertEqual(user['access_token'],
                         {'key': '0123456789',
                          'secret': 'xxx'})

        url = self.reverse_url('logout')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        response = self.client.get('/')
        self.assertEqual(response.code, 200)
        self.assertTrue('Login with Twitter' in response.body)

        self.assertEqual(int(self.redis.get('auths:total')), 1)
        self.assertEqual(int(self.redis.get('auths:username:peterbe')), 1)

    def test_twitter_login_twitter_failing(self):
        TwitterAuthHandler.get_authenticated_user = \
          make_twitter_get_authenticated_user_callback(None)
        url = self.reverse_url('auth_twitter')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('twitter.com' in response.headers['location'])

        response = self.client.get(url, {'oauth_token':'xxx'})
        self.assertEqual(response.code, 200)
        self.assertTrue("Sorry" in response.body)
        self.assertTrue("Try again" in response.body)

    def _login(self, username=u'peterbe', name=u'Peter Bengtsson',
                     email=None):
        struct = {
          'name': name,
          'username': username,
          'email': email,
          'access_token': {'key': '0123456789',
                           'secret': 'xxx'}
        }
        TwitterAuthHandler.get_authenticated_user = \
          make_twitter_get_authenticated_user_callback(struct)
        TwitterAuthHandler.authenticate_redirect = \
          twitter_authenticate_redirect
        url = self.reverse_url('auth_twitter')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue('twitter.com' in response.headers['location'])

        response = self.client.get(url, {'oauth_token':'xxx'})
        assert response.code == 302

    def test_home(self):
        url = self.reverse_url('test')
        response = self.client.get('/')
        self.assertEqual(response.code, 200)
        self.assertTrue('Login with Twitter to start' in response.body)

        self._login(username='peppe')
        response = self.client.get('/')
        self.assertEqual(response.code, 200)
        self.assertTrue('Login with Twitter to start' not in response.body)

    def test_test_service(self):
        url = self.reverse_url('test')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('auth_twitter') in
                        response.headers['location'])
        self._login()

        response = self.client.get(url)
        self.assertEqual(response.code, 200)


    def test_json(self):
        self.assertEqual(self.redis.get('lookups:json'), None)
        FollowsHandler.twitter_request = \
          make_mock_twitter_request({u'relationship': {
                   u'target': {u'followed_by': False,
                               u'following': False,
                               u'screen_name': u'obama'}}})

        url = self.reverse_url('json')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue('usernames' in struct['ERROR'])

        response = self.client.get(url, {'username': 'obama'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue('Not authorized' in struct['ERROR'])

        self._login()
        response = self.client.get(url, {'username': 'obama'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['obama'], False)

        # do it again and it should be picked up by the cache
        FollowsHandler.twitter_request = \
          make_mock_twitter_request({u'relationship': {
                   u'target': {u'followed_by': True,
                               u'following': True,
                               u'screen_name': u'obama'}}})
        response = self.client.get(url, {'username': 'obama'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['obama'], False)

        self.assertEqual(int(self.redis.get('lookups:json')), 2)
        self.assertEqual(int(self.redis.get('lookups:username:peterbe')), 2)
        self.assertEqual(int(self.redis.get('lookups:usernames')), 2)

    def test_json_with_overriding_you(self):
        FollowsHandler.twitter_request = \
          make_mock_twitter_request({u'relationship': {
                   u'target': {u'followed_by': False,
                               u'following': False,
                               u'screen_name': u'obama'}}})

        self._login()
        url = self.reverse_url('json')
        response = self.client.get(url, {'username': 'obama', 'you': 'bob'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertTrue(struct['ERROR'])

        url = self.reverse_url('jsonp')
        response = self.client.get(url, {'username': 'obama', 'you': 'bob'})
        self.assertEqual(response.code, 200)
        self.assertTrue('ERROR' in response.body)

        url = self.reverse_url('json')
        response = self.client.get(url, {'username': 'obama', 'you': 'peterbe'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['obama'], False)

        url = self.reverse_url('jsonp')
        response = self.client.get(url, {'username': 'obama', 'you': 'peterbe'})
        self.assertEqual(response.code, 200)
        self.assertTrue('"obama":' in response.body)
        self.assertTrue('false' in response.body)

        url = self.reverse_url('json')
        # do it again and it should be picked up by the cache
        FollowsHandler.twitter_request = \
          make_mock_twitter_request({u'relationship': {
                   u'target': {u'followed_by': True,
                               u'following': True,
                               u'screen_name': u'obama'}}})
        response = self.client.get(url, {'username': 'obama'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['obama'], False)


    def test_jsonp(self):
        FollowsHandler.twitter_request = \
          make_mock_twitter_request({u'relationship': {
                   u'target': {u'followed_by': False,
                               u'following': False,
                               u'screen_name': u'obama'}}})

        url = self.reverse_url('jsonp')
        self._login()
        response = self.client.get(url, {'username': 'obama'})
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'callback({"obama": false})')
        response = self.client.get(url, {'username': 'obama', 'callback': 'FOO'})
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, 'FOO({"obama": false})')

        self.assertEqual(int(self.redis.get('lookups:json')), 0)
        self.assertEqual(int(self.redis.get('lookups:jsonp')), 2)
        self.assertEqual(int(self.redis.get('lookups:username:peterbe')), 2)
        self.assertEqual(int(self.redis.get('lookups:usernames')), 2)

    def test_jsonp(self):
        url = self.reverse_url('jsonp')
        response = self.client.get(url, {'username': 'obama'})
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body.startswith('callback({"ERROR":'))
        response = self.client.get(url, {'username': 'obama', 'callback': 'FOO'})
        self.assertEqual(response.code, 200)
        self.assertTrue(response.body.startswith('FOO({"ERROR":'))

    def test_following_none_cached(self):
        FollowsHandler.twitter_request = \
          make_mock_twitter_request([
           {u'connections': [u'none'],
            u'name': u'Stephen Fry',
            u'screen_name': u'stephenfry'},
           {u'connections': [u'following', u'followed_by'],
            u'name': u'fox2mike',
            u'screen_name': u'fox2mike'}])

        url = self.reverse_url('json')
        self._login()
        response = self.client.get(url, {'usernames': 'stephenfry,fox2mike'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['stephenfry'], False)
        self.assertEqual(struct['fox2mike'], True)

        # do it again and both should be cached
        FollowsHandler.twitter_request = \
          make_mock_twitter_request([
           {u'connections': [u'following', u'followed_by'],
            u'name': u'Stephen Fry',
            u'screen_name': u'stephenfry'},
           {u'connections': [u'none'],
            u'name': u'fox2mike',
            u'screen_name': u'fox2mike'}])

        response = self.client.get(url, {'usernames': 'stephenfry,fox2mike'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['stephenfry'], False)
        self.assertEqual(struct['fox2mike'], True)

        FollowsHandler.twitter_request = \
          make_mock_twitter_request({u'relationship': {
                   u'target': {u'followed_by': True,
                               u'following': True,
                               u'screen_name': u'ashley'}}})

        response = self.client.get(url,
          {'usernames': 'stephenfry,fox2mike,ashley'})
        self.assertEqual(response.code, 200)
        struct = json.loads(response.body)
        self.assertEqual(struct['stephenfry'], False)
        self.assertEqual(struct['fox2mike'], True)
        self.assertEqual(struct['ashley'], True)

    def test_following(self):
        url = self.reverse_url('following', 'obama')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('auth_twitter') in
                        response.headers['location'])

        self._login()
        FollowingHandler.twitter_request = \
          make_mock_twitter_request({
            "/friendships/show": {u'relationship': {
                                    u'target': {u'followed_by': False,
                                    u'following': False,
                                    u'screen_name': u'obama'}}},
            "/users/show?screen_name=obama": {u'followers_count': 41700,
                            u'following': False,
                            u'friends_count': 1300,
                            u'name': u'Barak',
                            u'screen_name': u'obama',
                            },
            "/users/show?screen_name=peterbe": {
                            u'followers_count': 417,
                            u'following': False,
                            u'friends_count': 330,
                            u'name': u'Peter Bengtsson',
                            u'screen_name': u'peterbe',
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('<title>obama is too cool for me' in response.body)
        self.assertTrue('%.1f' % (41700.0/1300) in response.body)
        self.assertTrue('%.1f' % (417.0/330) in response.body)

        # same URL but different remote data should yield the same result
        # because of temporary caching
        FollowingHandler.twitter_request = \
          make_mock_twitter_request({
            "/friendships/show": {u'relationship': {
                                    u'target': {u'followed_by': True,
                                      u'following': True,
                                      u'screen_name': u'obama'}}},
            "/users/show?screen_name=obama": {u'followers_count': 41700,
                            u'following': False,
                            u'friends_count': 1301,
                            u'name': u'Barak',
                            u'screen_name': u'obama',
                            },
            "/users/show?screen_name=peterbe": {
                            u'followers_count': 417,
                            u'following': False,
                            u'friends_count': 331,
                            u'name': u'Peter Bengtsson',
                            u'screen_name': u'peterbe',
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('<title>obama is too cool for me' in response.body)
        self.assertTrue('%.1f' % (41700.0/1300) in response.body)
        self.assertTrue('%.1f' % (417.0/330) in response.body)

        url = self.reverse_url('following', 'chris')
        FollowingHandler.twitter_request = \
          make_mock_twitter_request({
            "/friendships/show": {u'relationship': {
                                    u'target': {u'followed_by': True,
                                      u'following': True,
                                      u'screen_name': u'chris'}}},
            "/users/show?screen_name=chris": {u'followers_count': 400,
                            u'following': True,
                            u'friends_count': 1000,
                            u'name': u'West',
                            u'screen_name': u'chris',
                            },
            })
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('<title>chris follows me' in response.body)
        self.assertTrue('%.1f' % (400.0/1000) in response.body)
        self.assertTrue('%.1f' % (417.0/330) in response.body)

    def test_following_temporary_glitch_on_info(self):
        url = self.reverse_url('following', 'obama')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('auth_twitter') in
                        response.headers['location'])

        self._login()
        FollowingHandler.twitter_request = \
          make_mock_twitter_request({
            "/friendships/show": {u'relationship': {
                                    u'target': {u'followed_by': False,
                                    u'following': False,
                                    u'screen_name': u'obama'}}},
            "/users/show?screen_name=obama": {u'followers_count': 41700,
                            u'following': False,
                            u'friends_count': 1300,
                            u'name': u'Barak',
                            u'screen_name': u'obama',
                            },
            "/users/show?screen_name=peterbe": None
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue("Sorry" in response.body)
        self.assertTrue("Unable to look up info for peterbe"
                        in response.body)

    def test_following_temporary_glitch_on_friendship(self):
        url = self.reverse_url('following', 'obama')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('auth_twitter') in
                        response.headers['location'])

        self._login()
        FollowingHandler.twitter_request = \
          make_mock_twitter_request({
            "/friendships/show": None,
            "/users/show?screen_name=obama": {u'followers_count': 41700,
                            u'following': False,
                            u'friends_count': 1300,
                            u'name': u'Barak',
                            u'screen_name': u'obama',
                            },
            "/users/show?screen_name=peterbe": {
                            u'followers_count': 417,
                            u'following': False,
                            u'friends_count': 330,
                            u'name': u'Peter Bengtsson',
                            u'screen_name': u'peterbe',
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue("Sorry" in response.body)
        self.assertTrue("Unable to look up friendship for obama"
                        in response.body)

    def test_following_someone_following_0(self):
        url = self.reverse_url('following', 'obama')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertTrue(self.reverse_url('auth_twitter') in
                        response.headers['location'])

        self._login()
        FollowingHandler.twitter_request = \
          make_mock_twitter_request({
            "/friendships/show": {u'relationship': {
                                    u'target': {u'followed_by': False,
                                    u'following': False,
                                    u'screen_name': u'obama'}}},
            "/users/show?screen_name=obama": {u'followers_count': 41700,
                            u'following': False,
                            u'friends_count': 0,
                            u'name': u'Barak',
                            u'screen_name': u'obama',
                            },
            "/users/show?screen_name=peterbe": {
                            u'followers_count': 417,
                            u'following': False,
                            u'friends_count': 330,
                            u'name': u'Peter Bengtsson',
                            u'screen_name': u'peterbe',
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('<title>obama is too cool for me' in response.body)
        self.assertTrue('%.1f' % (417.0/330) in response.body)
        self.assertTrue('%.1f' % (41700.0/1) in response.body)


def make_twitter_get_authenticated_user_callback(struct):
    def twitter_get_authenticated_user(self, callback, **kw):
        callback(struct)
    return twitter_get_authenticated_user

def twitter_get_authenticated_user(self, callback, **kw):
    callback({
      'name': u'Peter Bengtsson',
      'username': u'peterbe',
      'email': None,
      'access_token': {'key': '0123456789', 'secret': 'xxx'}
    })

def twitter_authenticate_redirect(self):
    self.redirect(self._OAUTH_AUTHENTICATE_URL)


def make_mock_twitter_request(result, path=None):
    def twitter_request(self, path, callback, **kw):
        """
        SINGLE FRIENDSHIP SHOW

        Sample response if it's someone really cool:

            {u'relationship': {u'source': {...
                                   u'followed_by': False,
                                   u'following': False,
                                   ...
                                   u'screen_name': u'peterbe',
                                   },
                       u'target': {u'followed_by': False,
                                   u'following': False,
                                   ...
                                   u'screen_name': u'ConanOBrien'}}}

        Sample response if you are being followed by someone:

            {u'relationship': {u'source': {...
                                   u'followed_by': True,
                                   u'following': False,
                                   ...
                                   u'screen_name': u'peterbe'},
                       u'target': {u'followed_by': False,
                                   u'following': True,
                                   ...
                                   u'screen_name': u'Dal'}}}

        Sample response if you follow each other:

            {u'relationship': {u'source': {...
                                   u'followed_by': True,
                                   u'following': True,
                                   u'screen_name': u'peterbe'},
                       u'target': {u'followed_by': True,
                                   u'following': True,
                                   ...
                                   u'screen_name': u'jlongster'}}}

        MULTIPLE FRIENDSHIP LOOKUP

        Both people follow:

            [{u'connections': [u'followed_by'],
              ...
              u'name': u'Toshiaki Toyama',
              u'screen_name': u'manboubird'},
             {u'connections': [u'following', u'followed_by'],
              ...
              u'name': u'Chris AtLee',
              u'screen_name': u'chrisatlee'}]

        One follows one doesn't:

            [{u'connections': [u'none'],
              ...
              u'name': u'Stephen Fry',
              u'screen_name': u'stephenfry'},
             {u'connections': [u'following', u'followed_by'],
              ...
              u'name': u'fox2mike',
              u'screen_name': u'fox2mike'}]

        """
        kw.pop('access_token')
        long_path = path + '?' + urlencode(kw)
        if isinstance(result, dict):
            send_back = result.get(long_path, result.get(path, result))
        else:
            send_back = result
        callback(send_back)
    return twitter_request
