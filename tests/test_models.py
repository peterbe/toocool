from unittest import TestCase
from models import User, connection
from .base import DatabaseTestCaseMixin

class ModelsTestCase(TestCase, DatabaseTestCaseMixin):

    def setUp(self):
        self.db = connection.test
        super(ModelsTestCase, self).setUp()
        self.setup_connection()

    def tearDown(self):
        self.teardown_connection()

    def test_create_user(self):
        assert not self.db.User.find().count()
        user = self.db.User()
        user.username = u'bob'
        user.access_token = {'key': 'xxx', 'secret': 'yyy'}
        user.save()

        b = user['modify_date']
        self.assertTrue(b)
        from time import sleep
        # mongodb is a bit weird when it comes to actual saving time
        # so introduce a realistic phsyical waiting time.
        sleep(0.001)
        user.username = u'bobby'
        user.save()

        a = user['modify_date']
        self.assertTrue(a.microsecond > b.microsecond)

    def test_find_by_username(self):
        tweeter = self.db.Tweeter()
        tweeter['user_id'] = 123
        tweeter['username'] = u'TheRock'
        tweeter['name'] = u'The Rock'
        tweeter['followers'] = 100
        tweeter['following'] = 100
        tweeter.save()

        self.assertTrue(self.db.Tweeter.find_by_username(self.db, 'THEROCK'))
        self.assertTrue(self.db.Tweeter.find_by_username(self.db, 'TheRock'))
        self.assertTrue(not self.db.Tweeter.find_by_username(self.db, 'RockThe'))
