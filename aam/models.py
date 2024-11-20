import datetime
import decimal

from dateutil.relativedelta import relativedelta

import peewee
import playhouse.shortcuts

import aam.utilities

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
    creation_date:datetime.date = peewee.DateField(null=True)
    closure_date: datetime.date = peewee.DateField(null=True)

    def get_bills(self) -> list[dict]:
        """Returns a list of dicts describing bills in the account between the creation date and the account closure
        date. If the account creation date is not set then return an empty list."""
        bills = []

        if self.closure_date:
            end = self.closure_date
        else:
            end = datetime.date.today()

        support_start_month = Month.get(Month.date==datetime.date(2024, 7,1))

        if self.creation_date:
            required_months = aam.utilities.get_bill_months(self.creation_date, end)
            for bill in self.bills:
                if bill.month.date in required_months:
                    new_bill = {"id": bill.id, "month": bill.month.date, "usage_dollar": bill.usage}
                    if bill.usage and bill.month >= support_start_month:
                            new_bill["support_charge"] = bill.usage * decimal.Decimal(0.1)
                            new_bill["total_pound"] = bill.month.exchange_rate * (bill.usage * decimal.Decimal(1.1))
                    elif bill.usage:
                            new_bill["support_charge"] = 0
                            new_bill["total_pound"] = bill.month.exchange_rate * bill.usage
                    bills.append(new_bill)
        return bills

    def final_date(self) -> datetime.date:
        if self.closure_date:
            return self.closure_date
        else:
            return datetime.date.today()

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

    def date_in_month(self, date: datetime.date) -> bool:
         """Returns true if date is in month."""
         if (self.date.month == date.month) and (self.date.year == date.year):
             return True
         return False

    def __gt__(self, other: "Month"):
        return self.date > other.date

    def __ge__(self, other: "Month"):
        return self.date >= other.date

    def __lt__(self, other: "Month"):
        return self.date < other.date

    def __le__(self, other: "Month"):
        return self.date <= other.date

class Bill(BaseModel):
    id = peewee.AutoField()
    account_id = peewee.ForeignKeyField(Account, backref="bills")
    month = peewee.ForeignKeyField(Month, backref="bills")
    usage = peewee.DecimalField(null=True)
    support_eligible = peewee.BooleanField(default=True)


class Recharge(BaseModel):
    id = peewee.AutoField()
    account_id = peewee.ForeignKeyField(Account, backref="recharges")
    month = peewee.ForeignKeyField(Month, backref="recharges")


db.create_tables([Account, LastAccountUpdate, Person, Sysadmin, Note, Month, Bill, Recharge])
