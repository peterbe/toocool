from base import BaseHTTPTestCase

class HandlersTestCase(BaseHTTPTestCase):

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.code, 200)
        self.assertTrue('stranger' in response.body)

    def test_twitter_login(self):
        pass

    def test_test_service(self):
        pass

    def test_json(self):
        pass

    def test_jsonp(self):
        pass

    def test_following_none_cached(self):
        pass

    def test_following_self_cached(self):
        pass

    def test_following_them_cached(self):
        pass

    def test_following_both_cached(self):
        pass
