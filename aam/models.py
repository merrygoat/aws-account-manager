import peewee
import playhouse.shortcuts

db = peewee.SqliteDatabase('data.db')


class DictMixin:
    def to_dict(self):
        return playhouse.shortcuts.model_to_dict(self)


class Account(peewee.Model, DictMixin):
    id = peewee.AutoField()
    account_id = peewee.CharField()
    name = peewee.CharField()
    account_status = peewee.CharField()

    class Meta:
        database = db


class Person(peewee.Model, DictMixin):
    id = peewee.AutoField()
    name = peewee.CharField()
    email = peewee.CharField()

    class Meta:
        database = db


db.create_tables([Account])


