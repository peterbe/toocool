#!/usr/bin/env python

import code, re
try:
    import here
except ImportError:
    import sys
    import os.path as op
    sys.path.insert(0, op.abspath(op.join(op.dirname(__file__), '..')))
    import here

if __name__ == '__main__':


    from models import User, Tweeter, connection
    from pymongo.objectid import InvalidId, ObjectId

    import settings
    db = connection[settings.DATABASE_NAME]
    print "AVAILABLE:"
    print '\n'.join(['\t%s'%x for x in locals().keys()
                     if re.findall('[A-Z]\w+|db|con', x)])
    print "Database available as 'db'"
    code.interact(local=locals())
