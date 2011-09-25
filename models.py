import datetime
from mongolite import Connection, Document
connection = Connection()

@connection.register
class User(Document):
    __collection__ = 'users'
    structure = {
      'username': unicode,
      'access_token': dict,
      'modify_date': datetime.datetime
    }

    default_values = {'modify_date':datetime.datetime.utcnow}

    def save(self, *args, **kwargs):
        if '_id' in self and kwargs.get('update_modify_date', True):
            self.modify_date = datetime.datetime.utcnow()
        super(User, self).save(*args, **kwargs)
