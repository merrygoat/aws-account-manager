import peewee
import playhouse.shortcuts

# Pragmas ensures foreign key constraints are enabled - they are disabled by default in SQLite.
db = peewee.SqliteDatabase('data.db', pragmas={'foreign_keys': 1})


class DictMixin:
    def to_dict(self):
        return playhouse.shortcuts.model_to_dict(self)


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Person(BaseModel, DictMixin):
    id = peewee.AutoField()
    first_name = peewee.CharField()
    last_name = peewee.CharField()
    email = peewee.CharField()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Account(BaseModel, DictMixin):
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField()
    email = peewee.CharField()
    status = peewee.CharField()
    budget_holder = peewee.ForeignKeyField(Person, backref="budget_holder", null=True)
    finance_code = peewee.CharField(null=True)
    task_code = peewee.CharField(null=True)
    billing_start = peewee.DateField(null=True)

class Sysadmin(BaseModel):
    id = peewee.AutoField()
    person = peewee.ForeignKeyField(Person, backref="sysadmin")
    account = peewee.ForeignKeyField(Account, backref="sysadmin")

    @property
    def full_name(self) -> str:
        return f"{self.person.first_name} {self.person.last_name}"

class LastAccountUpdate(BaseModel):
    id = peewee.IntegerField(primary_key=True)
    time = peewee.DateTimeField()

class Note(BaseModel):
    id = peewee.AutoField()
    date = peewee.DateField()
    text = peewee.CharField()
    account_id = peewee.ForeignKeyField(Account, backref="notes")

class Month(BaseModel):
    id = peewee.AutoField()
    date = peewee.DateField()
    exchange_rate = peewee.DecimalField()

class Bill(BaseModel):
    id = peewee.AutoField()
    account_id = peewee.ForeignKeyField(Account, backref="bills")
    month = peewee.ForeignKeyField(Month, backref="bills")
    usage = peewee.DecimalField()
    support_eligible = peewee.BooleanField()

class Recharge(BaseModel):
    id = peewee.AutoField()
    account_id = peewee.ForeignKeyField(Account, backref="recharges")
    month = peewee.ForeignKeyField(Month, backref="recharges")


db.create_tables([Account, LastAccountUpdate, Person, Sysadmin, Note, Month, Bill, Recharge])
