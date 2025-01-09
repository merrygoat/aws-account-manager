# This is where the databases tables and fields are defined.

# Where a foreign key is exposed on the parent object as a backref, I have added an annotated class object on the
# parent. This is not technically necessary but helps the IDE, as otherwise it marks backrefs as unknown when they are
# referenced.

import calendar
import datetime
import decimal
from decimal import Decimal
from collections.abc import Iterable

import peewee
from peewee import JOIN
from playhouse.hybrid import hybrid_property

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
    budget_holder: Iterable["Account"]  # backref
    sysadmin: Iterable["Sysadmin"]  # backref

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

class Organization(BaseModel):
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField(null=True)
    accounts: "Account"  # backref
    last_updated_time: Iterable["LastAccountUpdate"]  # backref
    shared_charges: Iterable["SharedCharge"]  # backref

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
    sysadmin: Iterable["Sysadmin"]  # backref
    notes: Iterable["Note"]  # backref
    transactions: Iterable["Transaction"]  # backref

    def get_transactions(self) -> list[dict]:
        """Returns a list of dicts describing month transactions in the account between the creation date and the
        account closure date. If the account creation date is not set then return an empty list."""
        if not self.creation_date:
            return []

        required_months = aam.utilities.get_months_between(self.creation_date, self.final_date())

        self._check_missing_monthly_transactions(required_months)

        required_transactions = (Transaction.select(Transaction, RechargeRequest.reference)
            .join(RechargeRequest, JOIN.LEFT_OUTER)
            .where((Transaction.month_code.in_(required_months)) & (Transaction.account == self.id)))

        transactions = [transaction.to_json() for transaction in required_transactions]
        return transactions

    def _check_missing_monthly_transactions(self, required_months: list[int]):
        """Accounts should have a usage transaction for each month the account is open. This function checks if the
        account has 'monthly' type transactions for each month code in `required_months`."""
        required_transactions = (Transaction.select().where((Transaction.month_code.in_(required_months)) & (Transaction.account == self.id) & (Transaction.type == "Monthly")))
        existing_transaction_months = [transaction.month_code for transaction in required_transactions]
        missing_months = set(required_months) - set(existing_transaction_months)
        if missing_months:
            for month_code in missing_months:
                date = datetime.date(year=aam.utilities.year_from_month_code(month_code), month=aam.utilities.month_from_month_code(month_code), day=1)
                Transaction.create(account=self.id, type="Monthly", date=date, is_pound=False)

    def final_date(self) -> datetime.date:
        """Return the final date on which the account is active."""
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
    account = peewee.ForeignKeyField(Account, backref="notes")

class Month(BaseModel):
    id = peewee.AutoField()
    month_code: int = peewee.IntegerField()
    exchange_rate: Decimal = peewee.DecimalField()
    shared_charges: Iterable["SharedCharge"]  # backref

    @property
    def year(self) -> int:
        return aam.utilities.year_from_month_code(self.month_code)

    @property
    def month(self) -> int:
        """Months start at 1, e.g. Jan = 1, Feb = 2"""
        return aam.utilities.month_from_month_code(self.month_code)

    def __repr__(self):
        return f"Month: {calendar.month_abbr[self.month]}-{self.year}"

    def __str__(self):
        return f"{calendar.month_abbr[self.month]}-{self.year}"

    def to_date(self):
        return datetime.date(self.year, self.month, 1)


class RechargeRequest(BaseModel):
    id = peewee.AutoField()
    date: datetime.date = peewee.DateField()
    reference = peewee.CharField()
    status = peewee.CharField()
    transactions: Iterable["Transaction"]  # backref

    def to_json(self):
        return {"id": self.id, "date": self.date, "reference": self.reference, "status": self.status}

class Transaction(BaseModel):
    id = peewee.AutoField()
    account = peewee.ForeignKeyField(Account, backref="transactions")
    type = peewee.CharField()  # ["Monthly", "Pre-pay", "Savings plan", "Adjustment"]
    date: datetime.date = peewee.DateField()
    amount: Decimal = peewee.DecimalField(null=True)  # The net value of the transaction
    is_pound = peewee.BooleanField()
    _exchange_rate: Decimal = peewee.DecimalField(null=True)   # USD/GBP
    recharge_request = peewee.ForeignKeyField(RechargeRequest, backref="transactions", null=True)

    def to_json(self) -> dict:
        transaction = {"id": self.id, "account_id": self.account.id, "type": self.type, "date": self.date,
                       "amount": self.amount}
        if self.is_pound:
            # Accounts are settled in pounds so there is no reason to convert a pound transaction to a dollar value
            transaction.update({"currency": "£", "support_charge": "-", "shared_charge": "-",
                                "total_pound": self.gross_total_pound})
        else:
            transaction.update({"currency": "$", "support_charge": self.support_charge,
                                "shared_charge": self.shared_charges, "exchange_rate": self.exchange_rate,
                                "gross_total_dollar": self.gross_total_dollar, "gross_total_pound": self.gross_total_pound})

        if self.recharge_request:
            transaction["recharge_reference"] = self.recharge_request.reference
        else:
            transaction["recharge_reference"] = "-"
        return transaction

    @hybrid_property
    def month_code(self) -> int:
        return aam.utilities.month_code(self.date.year, self.date.month)

    @property
    def month(self) -> Month:
        return Month.get(Month.month_code == self.month_code)

    @property
    def exchange_rate(self) -> decimal.Decimal:
        if self.type == "Monthly":
            return self.month.exchange_rate
        else:
            return self._exchange_rate

    @property
    def amount_pound(self) -> decimal.Decimal | None:
        if not self.amount:
            return None
        if self.is_pound:
            return self.amount
        else:
            return self.amount * self.exchange_rate

    @property
    def amount_dollar(self) -> decimal.Decimal | None:
        if not self.amount:
            return None
        if not self.is_pound:
            return self.amount
        else:
            if self.exchange_rate:
                return self.amount / self.exchange_rate
            else:
                return None

    @property
    def support_eligible(self) -> bool:
        """Accounts must pay 10% charge after 01/08/24 as this was when the OGVA started."""
        return (self.type == "Monthly") and (self.date >= datetime.date(2024, 8, 1))

    @property
    def support_charge(self) -> Decimal:
        """If the transaction needs to be charged for support, return the amount in dollars."""
        if self.support_eligible and self.amount_dollar:
            return self.amount_dollar * Decimal(0.1)
        else:
            return Decimal(0)

    @property
    def shared_charges(self) -> decimal.Decimal:
        if self.account.id is None or self.month.id is None:
            raise ValueError("Calculation of shared charges failed due to missing data.")
        total = decimal.Decimal(0)
        charges = (SharedCharge.select().where((AccountJoinSharedCharge.account == self.account.id) & (SharedCharge.month == self.month.id))
                   .join(AccountJoinSharedCharge))
        for charge in charges:
            total += charge.cost_per_account()
        return total

    @property
    def gross_total_dollar(self) -> Decimal | None:
        """Calculate the total cost for the month, adding 20% for VAT."""
        if self.amount is None or self.amount_dollar is None:
            return None
        else:
            return (self.amount_dollar + self.support_charge + self.shared_charges) * Decimal(1.2)

    @property
    def gross_total_pound(self) -> Decimal | None:
        """Calculate the total cost of the transaction, converting from dollars."""
        if self.is_pound:
            return self.amount
        if self.gross_total_dollar is None:
            return None
        else:
            return  self.gross_total_dollar * self.exchange_rate


class SharedCharge(BaseModel):
    id = peewee.AutoField()
    name = peewee.TextField()
    amount: decimal.Decimal = peewee.DecimalField()
    organization = peewee.ForeignKeyField(Organization, backref="shared_charges")
    month = peewee.ForeignKeyField(Month, backref="shared_charges")

    def to_dict(self):
        month = Month.get(Month.id == self.month)
        charges = (SharedCharge.select(Account.name).where(SharedCharge.id == self.id)
                   .join(AccountJoinSharedCharge)
                   .join(Account).dicts())
        account_names = [charge["name"] for charge in charges]
        account_names = ", ".join(sorted(account_names))

        return {"id": self.id, "name": self.name, "amount": self.amount, "month": str(month),
                "account_names": account_names}

    def num_accounts(self) -> int:
        return AccountJoinSharedCharge.select().where(AccountJoinSharedCharge.shared_charge == self.id).count()

    def cost_per_account(self) -> decimal.Decimal:
        return self.amount / self.num_accounts()


class AccountJoinSharedCharge(BaseModel):
    account = peewee.ForeignKeyField(Account, backref="shared_charges_join")
    shared_charge = peewee.ForeignKeyField(SharedCharge, backref="account_join", on_delete="CASCADE")

    class Meta:
        primary_key = peewee.CompositeKey('account', 'shared_charge')


db.create_tables([Account, LastAccountUpdate, Person, Sysadmin, Note, Month, Transaction, RechargeRequest,
                  SharedCharge, AccountJoinSharedCharge, Organization])
