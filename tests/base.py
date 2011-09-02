import base64
import time
import datetime
import mimetypes
import os
import re
import hmac
import hashlib
import unittest

from tornado.testing import LogTrapTestCase, AsyncHTTPTestCase

import app
from tornado_utils.http_test_client import TestClient, HTTPClientMixin

class _DatabaseTestCaseMixin(object):
    _once = False

    def setup_connection(self):
        if not self._once:
            self._once = True
            #self.db =

    def teardown_connection(self):
        # do this every time
        pass
        #self._emptyCollections()

    def _emptyCollections(self):
        pass



class BaseAsyncTestCase(AsyncHTTPTestCase, _DatabaseTestCaseMixin):

    def setUp(self):
        super(BaseAsyncTestCase, self).setUp()
        self.setup_connection()

    def tearDown(self):
        super(BaseAsyncTestCase, self).tearDown()
        self.teardown_connection()


class BaseHTTPTestCase(BaseAsyncTestCase, HTTPClientMixin):

    #_once = False
    def setUp(self):
        super(BaseHTTPTestCase, self).setUp()

        self._app.settings['email_backend'] = \
          'utils.send_mail.backends.locmem.EmailBackend'
        self._app.settings['email_exceptions'] = False
        self.client = TestClient(self)

    def tearDown(self):
        super(BaseHTTPTestCase, self).tearDown()
        self.db.flushall()

    def get_app(self):
        return app.Application(database_name='test')

    @property
    def db(self):
        return self.get_app().redis

    def decode_cookie_value(self, key, cookie_value):
        try:
            return re.findall('%s=([\w=\|]+);' % key, cookie_value)[0]
        except IndexError:
            raise ValueError("couldn't find %r in %r" % (key, cookie_value))

    def reverse_url(self, *args, **kwargs):
        return self._app.reverse_url(*args, **kwargs)


    ## these two are shamelessly copied from tornado.web.RequestHandler
    ## because in the _login() we have no access to a request and
    ## we need to be able to set a cookie
    def create_signed_value(self, name, value):
        """Signs and timestamps a string so it cannot be forged.

        Normally used via set_secure_cookie, but provided as a separate
        method for non-cookie uses.  To decode a value not stored
        as a cookie use the optional value argument to get_secure_cookie.
        """
        timestamp = str(int(time.time()))
        value = base64.b64encode(value)
        signature = self._cookie_signature(name, value, timestamp)
        value = "|".join([value, timestamp, signature])
        return value

    def _cookie_signature(self, *parts):
        hash = hmac.new(self._app.settings["cookie_secret"],
                        digestmod=hashlib.sha1)
        for part in parts: hash.update(part)
        return hash.hexdigest()

    def _get_html_attributes(self, tag, html):
        _elem_regex = re.compile('<%s (.*?)>' % tag, re.M | re.DOTALL)
        _attrs_regex = re.compile('(\w+)="([^"]+)"')
        all_attrs = []
        for input in _elem_regex.findall(html):
            all_attrs.append(dict(_attrs_regex.findall(input)))
        return all_attrs
