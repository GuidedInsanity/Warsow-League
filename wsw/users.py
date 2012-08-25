from flask.ext.login import (UserMixin, AnonymousUser)


class User(UserMixin):
    def __init__(self, name, id, admin=False, active=True):
        self.name = name
        self.id = id
        self.active = active
        self.admin = admin

    def is_active(self):
        return self.active

    def is_admin(self):
        return self.admin


class Anonymous(AnonymousUser):
    name = u"Anonymous"
    admin = False

    def is_admin(self):
        return False
