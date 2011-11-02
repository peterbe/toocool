import datetime
import os
import json
from urllib import urlencode
import tornado.escape
from .base import BaseHTTPTestCase
from handlers import (TwitterAuthHandler, FollowsHandler, FollowingHandler,
                      EveryoneIFollowJSONHandler)

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
        assert username
        struct = {
          'name': name,
          'screen_name': username,
          'email': email,
          'access_token': {'key': '0123456789',
                           'secret': 'xxx'},
          'id': 9999999999,
          'followers_count': 333,
          'friends_count': 222,
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


    def test_json_failing_twitter_api(self):
        self.assertEqual(self.redis.get('lookups:json'), None)
        FollowsHandler.twitter_request = \
          make_mock_twitter_request({
            "/friendships/lookup": None
            })

        self._login()

        url = self.reverse_url('json')
        import handlers
        from mock import patch
        with patch('handlers.time') as mock_time:
            response = self.client.get(url, {'usernames': ['obama', 'kimk']})
            self.assertEqual(response.code, 200)
            struct = json.loads(response.body)
            self.assertTrue(struct['ERROR'])

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

        self.assertEqual(self.db.Following
                         .find_one({'user': 'obama'})['following'],
                         False)

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

        self.assertEqual(self.db.Following
                         .find_one({'user': 'stephenfry'})['following'],
                         False)
        self.assertEqual(self.db.Following
                         .find_one({'user': 'fox2mike'})['following'],
                         True)

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

        self.assertEqual(self.db.Following
                         .find_one({'user': 'stephenfry'})['following'],
                         False)
        self.assertEqual(self.db.Following
                         .find_one({'user': 'fox2mike'})['following'],
                         True)
        self.assertEqual(self.db.Following
                         .find_one({'user': 'ashley'})['following'],
                         True)

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
                            'id': 9876543210,
                            },
            "/users/show?screen_name=peterbe": {
                            u'followers_count': 417,
                            u'following': False,
                            u'friends_count': 330,
                            u'name': u'Peter Bengtsson',
                            u'screen_name': u'peterbe',
                            'id': 123456789,
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('<title>obama is too cool for me' in response.body)
        self.assertTrue('%.1f' % (41700.0/1300) in response.body)
        self.assertTrue('%.1f' % (417.0/330) in response.body)

        following = self.db.Following.find_one({'user': 'obama'})
        assert following
        self.assertEqual(following,
                         self.db.Following.find_one({'user': 'obama',
                                                     'follows': 'peterbe'}))
        self.assertTrue(not following['following'])
        self.assertTrue(not self.db.Following.find_one({'user': 'peterbe'}))

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
                            'id': 9876543210,
                            },
            "/users/show?screen_name=peterbe": {
                            u'followers_count': 417,
                            u'following': False,
                            u'friends_count': 331,
                            u'name': u'Peter Bengtsson',
                            u'screen_name': u'peterbe',
                            'id': 123456789,
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('<title>obama is too cool for me' in response.body)
        self.assertTrue('%.1f' % (41700.0/1300) in response.body)
        self.assertTrue('%.1f' % (417.0/330) in response.body)

        following = self.db.Following.find_one({'user': 'obama'})
        assert following
        self.assertTrue(not following['following'])
        self.assertTrue(not self.db.Following.find_one({'user': 'peterbe'}))

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
                            'id': 112233445566,
                            },
            })
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('<title>chris follows me' in response.body)
        self.assertTrue('%.1f' % (400.0/1000) in response.body)
        self.assertTrue('%.1f' % (417.0/330) in response.body)

        following = self.db.Following.find_one({'user': 'chris'})
        assert following
        self.assertTrue(following['following'])
        self.assertTrue(not self.db.Following.find_one({'user': 'peterbe'}))
################################################################################
        self.assertEqual(following,
                         self.db.Following.find_one({'user': 'chris',
                                                     'follows': 'peterbe'}))


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
                            u'id': 1233456365
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
                            'id': 987654321,
                            },
            "/users/show?screen_name=peterbe": {
                            u'followers_count': 417,
                            u'following': False,
                            u'friends_count': 330,
                            u'name': u'Peter Bengtsson',
                            u'screen_name': u'peterbe',
                            'id': 123456789
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('<title>obama is too cool for me' in response.body)
        self.assertTrue('%.1f' % (417.0/330) in response.body)
        self.assertTrue('%.1f' % (41700.0/1) in response.body)

    def test_screenshots(self):
        from handlers import ScreenshotsHandler
        url = self.reverse_url('screenshots')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        static_base_path = os.path.join(
          self.get_app().settings['static_path'],
          'images',
          'screenshots',
        )
        for filename, title in ScreenshotsHandler.IMAGES:
            filepath = os.path.join(static_base_path, filename)
            self.assertTrue(os.path.isfile(filepath))
            filepath_small = filepath.replace('.png', '_small.png')
            self.assertTrue(os.path.isfile(filepath_small))

            self.assertTrue(filepath.replace(static_base_path, '')
                            in response.body)

            self.assertTrue(filepath_small.replace(static_base_path, '')
                            in response.body)

            self.assertTrue('alt="%s"' % title in response.body)
            self.assertTrue('title="%s"' % title in response.body)

    def test_everyone_json(self):
        url = self.reverse_url('everyone_json')
        response = self.client.get(url)
        self.assertEqual(response.code, 403)
        self._login()

        EveryoneIFollowJSONHandler.twitter_request = \
          make_mock_twitter_request({
            "/friends/ids": [123456789, 987654321],
            "/users/lookup": [
              {'id': 987654321,
               'followers_count': 41700,
               'following': False,
               'friends_count': 0,
               'name': u'Barak',
               'screen_name': u'obama',
               'status': {
                 'created_at': u'Wed Oct 12 20:12:27 +0000 2011',
                 }
               },
              {'id': 123456789,
               u'followers_count': 417,
               u'following': False,
               u'friends_count': 330,
               u'name': u'Peter Bengtsson',
               u'screen_name': u'peter',
               'created_at': u'Thu Jan 04 17:13:11 +0000 2007',
               }
            ]
        })

        response = self.client.get(url)
        struct = json.loads(response.body)
        self.assertEqual(struct, ['obama', 'peter'])

        # this should have created some Tweeters
        self.assertEqual(self.db.Tweeter
                         .find({'username': {'$ne':'peterbe'}})
                         .count(), 2)
        obama = self.db.Tweeter.find_one({'username': 'obama'})
        self.assertEqual(obama['user_id'], 987654321)
        self.assertEqual(obama['ratio'], 41700.0)
        self.assertEqual(obama['following'], 0)
        self.assertEqual(obama['followers'], 41700)
        self.assertEqual(obama['name'], 'Barak')
        fmt = '%Y-%m-%d-%H-%M-%S'
        self.assertEqual(
          obama['last_tweet_date'].strftime(fmt),
          datetime.datetime(2011, 10, 12, 20, 12, 27).strftime(fmt)
        )

        peter = self.db.Tweeter.find_one({'username': 'peter'})
        self.assertEqual(peter['user_id'], 123456789)
        self.assertEqual(peter['ratio'], 417.0/330)
        self.assertEqual(peter['following'], 330)
        self.assertEqual(peter['followers'], 417)
        self.assertEqual(peter['name'], 'Peter Bengtsson')
        self.assertEqual(peter['last_tweet_date'], None)

    def test_everyone_json_twitter_failing(self):
        url = self.reverse_url('everyone_json')
        response = self.client.get(url)
        self.assertEqual(response.code, 403)
        self._login()

        EveryoneIFollowJSONHandler.twitter_request = \
          make_mock_twitter_request({
            "/friends/ids": [123456789, 987654321],
            "/users/lookup": None
        })

        import handlers
        from mock import patch
        with patch('handlers.time') as mock_time:
            response = self.client.get(url)
            assert mock_time.sleep.called
            assert mock_time.sleep.call_count > 1
            struct = json.loads(response.body)
            self.assertTrue(struct['ERROR'])


    def test_lookups(self):
        url = self.reverse_url('lookups')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body.count('>0<'), 5)

        # fake in some redis data
        self.redis.set('lookups:json', 1111)
        self.redis.set('lookups:jsonp', 2222)
        self.redis.set('auths:total', 666)
        self.redis.set('lookups:usernames', 5555555)

        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body.count('>0<'), 0)
        self.assertTrue('>5,555,555<' in response.body)
        self.assertTrue('>3,333<' in response.body)
        self.assertTrue('>1,111<' in response.body)
        self.assertTrue('>2,222<' in response.body)
        self.assertTrue('>666<' in response.body)

    def test_everyone(self):
        url = self.reverse_url('everyone')
        response = self.client.get(url)
        self.assertEqual(response.code, 302)

        self._login()
        response = self.client.get(url)
        self.assertEqual(response.code, 200)

    def test_following_compared_to_not_logged_in(self):
        url = self.reverse_url('following_compared', 'obama', 'peterbe')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Sorry' in response.body)

        login_url = self.reverse_url('auth_twitter')
        self.assertTrue('href="%s?next=%s"' % (login_url, url)
                        in response.body)

    def test_following_compared_to_not_logged_in_one_tweeter_known(self):
        obama = self.db.Tweeter()
        obama['user_id'] = 12345
        obama['username'] = u'obama'
        obama['name'] = u'Barak Obama'
        obama['followers'] = 12350
        obama['following'] = 100
        obama.save()

        url = self.reverse_url('following_compared', 'obama', 'peterbe')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Sorry' in response.body)

        login_url = self.reverse_url('auth_twitter')
        self.assertTrue('href="%s?next=%s"' % (login_url, url)
                        in response.body)

        url = self.reverse_url('following_compared', 'peterbe', 'obama')
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        self.assertTrue('Sorry' in response.body)

        login_url = self.reverse_url('auth_twitter')
        self.assertTrue('href="%s?next=%s"' % (login_url, url)
                        in response.body)

    def test_following_compared_logged_in_self(self):
        url = self.reverse_url('following_compared', 'obama', 'peterbe')
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
                            'id': 9876543210,
                            },
            "/users/show?screen_name=peterbe": {
                            u'followers_count': 417,
                            u'following': False,
                            u'friends_count': 330,
                            u'name': u'Peter Bengtsson',
                            u'screen_name': u'peterbe',
                            'id': 123456789,
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        self.assertTrue('is too cool for peterbe' in response.body)
        self.assertTrue('<title>obama is too cool for peterbe'
                        in response.body)

    def test_following_compared_logged_in_different(self):
        url = self.reverse_url('following_compared', 'obama', 'kimk')
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
                            'id': 9876543210,
                            },
            "/users/show?screen_name=kimk": {
                            u'followers_count': 40117,
                            u'following': False,
                            u'friends_count': 200,
                            u'name': u'Kim Kardashian',
                            u'screen_name': u'kimk',
                            'id': 123456789,
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        self.assertTrue('is too cool for kimk' in response.body)
        self.assertTrue('<title>obama is too cool for kimk'
                        in response.body)

        obama = self.db.Tweeter.find_one({'username': 'obama'})
        self.assertEqual(obama['ratio'], 41700.0 / 1300)
        self.assertEqual(obama['ratio_rank'], 2)

        kimk = self.db.Tweeter.find_one({'username': 'kimk'})
        self.assertEqual(kimk['ratio'], 40117.0 / 200)
        self.assertEqual(kimk['ratio_rank'], 1)

    def test_suggest_tweet(self):
        url = self.reverse_url('suggest_tweet')
        response = self.client.get(url)
        self.assertEqual(response.code, 400)

        response = self.client.get(url, {'username': 'obama'})
        self.assertEqual(response.code, 403)

        self._login()
        obama = self.db.Tweeter()
        obama['username'] = u'obama'
        obama['name'] = u'Barak Obama'
        obama['user_id'] = 123456789
        obama['followers'] = 98765
        obama['following'] = 1000
        obama.set_ratio()
        obama.save()

        response = self.client.get(url, {'username': 'obama'})
        self.assertEqual(response.code, 200)

        struct = json.loads(response.body)
        self.assertTrue(len(struct['text']) <= 140)
        #self.assertTrue(struct['text'].endswith('#toocool'))
        self.assertTrue('@obama' in struct['text'])
        self.assertTrue('66 times cooler' in struct['text'])

        billy = self.db.Tweeter()
        billy['username'] = u'Mr_Billy_Nomates'
        billy['name'] = u'Billy Nomates von Longname'
        billy['user_id'] = 333334444
        billy['followers'] = 45
        billy['following'] = 100
        billy.set_ratio()
        billy.save()

        response = self.client.get(url, {'username': 'Mr_Billy_Nomates'})
        self.assertEqual(response.code, 200)

        struct = json.loads(response.body)
        self.assertTrue(len(struct['text']) <= 140)
        self.assertTrue('@Mr_Billy_Nomates' in struct['text'])

        peterbe = self.db.Tweeter.find_one({'username': 'peterbe'})
        twin = self.db.Tweeter()
        twin['username'] = u'peterbestwin'
        twin['name'] = u'Someone Likeme'
        twin['user_id'] = 111112222
        twin['followers'] = peterbe['followers'] + 1
        twin['following'] = peterbe['following'] - 1
        twin.set_ratio()
        twin.save()

        response = self.client.get(url, {'username': 'peterbestwin'})
        self.assertEqual(response.code, 200)

        struct = json.loads(response.body)
        self.assertTrue(len(struct['text']) <= 140)
        #self.assertTrue(struct['text'].endswith('#toocool'))
        self.assertTrue('@peterbestwin' in struct['text'])

    def test_default_page_not_found(self):
        url = '/does/not/exist'
        response = self.client.get(url)
        self.assertEqual(response.code, 302)
        self.assertEqual(response.headers['location'], '/does/not/exist/')

        url = '/does/not/exist/'
        response = self.client.get(url)
        self.assertEqual(response.code, 404)
        self.assertTrue('restart your computer' in response.body)

    def test_following_compared_refresh(self):
        url = self.reverse_url('following_compared', 'obama', 'kimk')
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
                            u'name': u'Barak Obama',
                            u'screen_name': u'obama',
                            'id': 9876543210,
                            },
            "/users/show?screen_name=kimk": {
                            u'followers_count': 40117,
                            u'following': False,
                            u'friends_count': 200,
                            u'name': u'Kim Kardashian',
                            u'screen_name': u'kimk',
                            'id': 123456789,
                            }
            })

        response = self.client.get(url)
        self.assertEqual(response.code, 200)

        obama = self.db.Tweeter.find_one({'username': 'obama'})
        self.assertEqual(obama['ratio'], 41700.0 / 1300)
        self.assertTrue('%.1f' % (41700.0 / 1300) in response.body)

        kimk = self.db.Tweeter.find_one({'username': 'kimk'})
        self.assertEqual(kimk['ratio'], 40117.0 / 200)
        self.assertTrue('%.1f' % (40117.0 / 200) in response.body)

        # change the stats
        import tasks
        def mock_twitter_request(self, url, callback, access_token, screen_name):
            results = {
              'obama': {
                u'followers_count': 40700,
                u'following': False,
                u'friends_count': 1333,
                u'name': u'Barak Obama',
                u'screen_name': u'obama',
                'id': 9876543210,
              },
              'kimk': {
                u'followers_count': 41117,
                u'following': False,
                u'friends_count': 222,
                u'name': u'Kim Kardashian',
                u'screen_name': u'kimk',
                'id': 123456789,
                }
            }
            class R(object):
                def __init__(self, result):
                    self.body = tornado.escape.json_encode(result)
            callback(R(results[screen_name]))

        tasks.UserUpdate.twitter_request = mock_twitter_request

        # now, pretend time passes
        obama['modify_date'] -= datetime.timedelta(seconds=60 * 60 + 1)
        obama.save(update_modify_date=False)
        kimk['modify_date'] -= datetime.timedelta(seconds=60 * 60 + 1)
        kimk.save(update_modify_date=False)

        # second time it's going to use the saved data
        response = self.client.get(url)
        self.assertEqual(response.code, 200)
        # the old numbers will still be there
        self.assertTrue('%.1f' % (41700.0 / 1300) in response.body)
        self.assertTrue('%.1f' % (40117.0 / 200) in response.body)

        # but the actual numbers will be updated!
        obama = self.db.Tweeter.find_one({'username': 'obama'})
        self.assertEqual(obama['ratio'], 40700.0 / 1333)  # new

        kimk = self.db.Tweeter.find_one({'username': 'kimk'})
        self.assertEqual(kimk['ratio'], 41117.0 / 222)  # new

def make_twitter_get_authenticated_user_callback(struct):
    def twitter_get_authenticated_user(self, callback, **kw):
        callback(struct)
    return twitter_get_authenticated_user

def twitter_get_authenticated_user(self, callback, **kw):
    callback({
      'name': u'Peter Bengtsson',
      'username': u'peterbe',
      'email': None,
      'access_token': {'key': '0123456789', 'secret': 'xxx'},
      'id': 1111111111,
      'screen_name': u'peterbe',
      'followers_count': 300,
      'friends_count': 255,
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
        if 'access_token' in kw:
            kw.pop('access_token')
        long_path = path + '?' + urlencode(kw)
        if isinstance(result, dict):
            send_back = result.get(long_path, result.get(path, result))
        else:
            send_back = result
        callback(send_back)
    return twitter_request
