import peewee
import playhouse.shortcuts

db = peewee.SqliteDatabase('data.db')


class DictMixin:
    def to_dict(self):
        return playhouse.shortcuts.model_to_dict(self)


class Account(peewee.Model, DictMixin):
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField()
    email = peewee.CharField()
    status = peewee.CharField()

    class Meta:
        database = db


class Person(peewee.Model, DictMixin):
    name = peewee.CharField()
    email = peewee.CharField()

    class Meta:
        database = db


class LastAccountUpdate(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    time = peewee.DateTimeField()

    class Meta:
        database = db

db.create_tables([Account, LastAccountUpdate])


