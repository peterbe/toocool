#!/usr/bin/env python
try:
    import here
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    import here

import time
import cPickle
import os.path
import logging
from glob import glob
import tornado.options
from tornado.options import define, options

define("verbose", default=False, help="be louder", type=bool)
define("debug", default=False, help="run in debug mode", type=bool)
define("dry_run", default=False, help="print messages to send", type=bool)

def main():
    from tornado_utils.send_mail import config
    filenames = glob(os.path.join(config.PICKLE_LOCATION, '*.pickle'))
    filenames.sort()
    if not filenames:
        return

    t0 = time.time()
    tornado.options.parse_command_line()
    if options.debug or options.dry_run:
        from tornado_utils.send_mail.backends.console import EmailBackend
    else:
        from tornado_utils.send_mail.backends.smtp import EmailBackend
    max_count = 10
    filenames = filenames[:max_count]
    messages = [cPickle.load(open(x, 'rb')) for x in filenames]
    backend = EmailBackend()
    backend.send_messages(messages)
    if not options.dry_run:
        for filename in filenames:
            if options.verbose:
                print "SENT", filename
            os.remove(filename)
    t1 = time.time()
    if options.verbose:
        print ("Sent %s messages in %s seconds" %
          (len(filenames), t1 - t0))

if __name__ == "__main__":
    main()
