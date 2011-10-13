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
