import calendar
import datetime
import decimal
from decimal import Decimal

import peewee
from peewee import JOIN

import aam.utilities

# Pragmas ensures foreign key constraints are enabled - they are disabled by default in SQLite.
db = peewee.SqliteDatabase('data.db', pragmas={'foreign_keys': 1})


class BaseModel(peewee.Model):
    class Meta:
        database = db


class Person(BaseModel):
    id = peewee.AutoField()
    first_name = peewee.CharField()
    last_name = peewee.CharField()
    email = peewee.CharField()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

class Organization(BaseModel):
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField(null=True)

class Account(BaseModel):
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField()
    organization = peewee.ForeignKeyField(Organization, backref='accounts', null=True)
    email = peewee.CharField()
    status = peewee.CharField()   # ACTIVE, SUSPENDED or Closed
    budget_holder = peewee.ForeignKeyField(Person, backref="budget_holder", null=True)
    finance_code = peewee.CharField(null=True)
    task_code = peewee.CharField(null=True)
    creation_date: datetime.date = peewee.DateField(null=True)
    closure_date: datetime.date = peewee.DateField(null=True)

    def get_bills(self) -> list[dict]:
        """Returns a list of dicts describing bills in the account between the creation date and the account closure
        date. If the account creation date is not set then return an empty list."""
        bills = []

        if self.closure_date:
            end = self.closure_date
        else:
            end = datetime.date.today()

        if self.creation_date:
            required_months = aam.utilities.get_months_between(self.creation_date, end)
            required_bills = (Bill.select(Bill.id, Month.month_code, Bill.usage, Bill.account_id, Month.id, Month.exchange_rate, Recharge.id, RechargeRequest.reference)
                              .join(Month)
                              .join(Recharge, JOIN.LEFT_OUTER, on=((Recharge.month == Month.id) & (Recharge.account == Bill.account_id)))
                              .join(RechargeRequest, JOIN.LEFT_OUTER)
                              .where((Month.month_code.in_(required_months)) & (Bill.account_id == self.id)))

            for bill in required_bills:
                new_bill = {"id": bill.id, "month_code": bill.month.month_code, "month_date": bill.month.to_date(),
                            "usage_dollar": bill.usage, "support_charge": bill.support_charge(),
                            "shared_charges": bill.shared_charges(), "total_dollar": bill.total_dollar(), "total_pound": bill.total_pound()}
                if hasattr(bill.month, "recharge"):
                    new_bill["recharge_reference"] = bill.month.recharge.recharge_request.reference
                else:
                    new_bill["recharge_reference"] = "-"
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
    organization = peewee.ForeignKeyField(Organization, backref="last_updated_time")
    time = peewee.DateTimeField(null=True)

class Note(BaseModel):
    id = peewee.AutoField()
    date = peewee.DateField()
    text = peewee.CharField()
    account_id = peewee.ForeignKeyField(Account, backref="notes")

class Month(BaseModel):
    id = peewee.AutoField()
    month_code: int = peewee.IntegerField()
    exchange_rate = peewee.DecimalField()

    @property
    def year(self) -> int:
        return (self.month_code - 1) // 12

    @property
    def month(self):
        """Months start at 1, e.g. Jan = 1, Feb = 2"""
        month = self.month_code % 12
        if month == 0:
            month = 12
        return month

    def __repr__(self):
        return f"Month: {calendar.month_abbr[self.month]}-{self.year}"

    def __str__(self):
        return f"{calendar.month_abbr[self.month]}-{self.year}"

    def to_date(self):
        return datetime.date(self.year, self.month, 1)

class Bill(BaseModel):
    id = peewee.AutoField()
    account_id = peewee.ForeignKeyField(Account, backref="bills")
    month = peewee.ForeignKeyField(Month, backref="bills")
    usage: decimal.Decimal = peewee.DecimalField(null=True)

    def support_eligible(self):
        """Accounts must pay 10% charge after 01/08/24 as this was when the OGVA started."""
        return self.month.month_code >= 2024 * 12 + 8

    def support_charge(self) -> Decimal | None:
        if self.usage is None:
            return None
        if self.support_eligible():
            return self.usage * Decimal(0.1)
        else:
            return Decimal(0)

    def shared_charges(self) -> decimal.Decimal:
        if self.account_id.id is None or self.month.id is None:
            raise ValueError("Calculation of shared charges failed due to missing data.")
        total = decimal.Decimal(0)
        charges = (SharedCharge.select().where((AccountJoinSharedCharge.account_id == self.account_id.id) & (SharedCharge.month_id == self.month.id))
                   .join(AccountJoinSharedCharge))
        for charge in charges:
            total += charge.cost_per_account()
        return total

    def total_dollar(self) -> Decimal | None:
        """Calculate the total bill for the month."""
        if self.usage is None:
            return None
        else:
            return self.usage + self.support_charge() + self.shared_charges()

    def total_pound(self) -> Decimal | None:
        """Calculate the total bill for the month."""
        total_dollar = self.total_dollar()
        if total_dollar is None:
            return None
        else:
            return  self.total_dollar() * self.month.exchange_rate


class RechargeRequest(BaseModel):
    id = peewee.AutoField()
    date: datetime.date = peewee.DateField()
    reference = peewee.CharField()


class Recharge(BaseModel):
    id = peewee.AutoField()
    account = peewee.ForeignKeyField(Account, backref="recharges")
    month = peewee.ForeignKeyField(Month, backref="recharges")
    recharge_request = peewee.ForeignKeyField(RechargeRequest, backref="recharges")


class SharedCharge(BaseModel):
    id = peewee.AutoField()
    name = peewee.TextField()
    amount: decimal.Decimal = peewee.DecimalField()
    organization = peewee.ForeignKeyField(Organization, backref="shared_charges")
    month_id = peewee.ForeignKeyField(Month, backref="shared_charges")

    def to_dict(self):
        month = Month.get(Month.id == self.month_id)
        charges = (SharedCharge.select(Account.name).where(SharedCharge.id == self.id)
                   .join(AccountJoinSharedCharge)
                   .join(Account).dicts())
        account_names = [charge["name"] for charge in charges]
        account_names = ", ".join(sorted(account_names))

        return {"id": self.id, "name": self.name, "amount": self.amount, "month": str(month),
                "account_names": account_names}

    def num_accounts(self) -> int:
        return AccountJoinSharedCharge.select().where(AccountJoinSharedCharge.shared_charge_id == self.id).count()

    def cost_per_account(self) -> decimal.Decimal:
        return self.amount / self.num_accounts()


class AccountJoinSharedCharge(BaseModel):
    account_id = peewee.ForeignKeyField(Account, backref="shared_charges_join")
    shared_charge_id = peewee.ForeignKeyField(SharedCharge, backref="account_join", on_delete="CASCADE")

    class Meta:
        primary_key = peewee.CompositeKey('account_id', 'shared_charge_id')


db.create_tables([Account, LastAccountUpdate, Person, Sysadmin, Note, Month, Bill, Recharge, RechargeRequest,
                  SharedCharge, AccountJoinSharedCharge, Organization])
