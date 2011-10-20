#!/usr/bin/env python

import code, re
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
