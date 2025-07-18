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

import aam.utilities
from aam.config import CONFIG

# Pragmas ensures foreign key constraints are enabled - they are disabled by default in SQLite.
db = peewee.SqliteDatabase(CONFIG["db_location"], pragmas={'foreign_keys': 1})

TRANSACTION_TYPES = ["Pre-pay", "Savings Plan", "Adjustment", "Recharge", "Starting Balance", "Unrecovered spend", "Monthly Usage"]

class BaseModel(peewee.Model):
    class Meta:
        database = db

class Organization(BaseModel):
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField(null=True)
    accounts: "Account"  # backref
    last_updated_time: Iterable["LastAccountUpdate"]  # backref

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

class LastAccountUpdate(BaseModel):
    id = peewee.IntegerField(primary_key=True)
    organization = peewee.ForeignKeyField(Organization, backref="last_updated_time")
    time = peewee.DateTimeField(null=True)

class Month(BaseModel):
    month_code: int = peewee.IntegerField(primary_key=True)
    exchange_rate: Decimal = peewee.DecimalField()

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
    start_date: datetime.date = peewee.DateField()
    end_date: datetime.date = peewee.DateField()
    reference = peewee.CharField()
    status = peewee.CharField()
    transactions: Iterable["Transaction"]  # backref
    monthly_usage: Iterable["MonthlyUsage"]  # backref

    def to_json(self):
        return {"id": self.id, "start_date": self.start_date, "end_date": self.end_date, "reference": self.reference,
                "status": self.status}

    def get_transactions(self, account_id: str = None) -> list:
        """Get Transaction and MonthlyUsage items associated with the """
        object_types = [Transaction, MonthlyUsage]
        items = []

        for object_type in object_types:
            if account_id is None:
                where_expression = object_type.recharge_request == self.id
            else:
                where_expression = (object_type.recharge_request == self.id) & (Account.id == account_id)

            items.extend(list((object_type.select(object_type, Account, Person)
                               .join(Account)
                               .join(Person, JOIN.LEFT_OUTER)
                               .where(where_expression))))
        return items


class Account(BaseModel):
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField()
    organization = peewee.ForeignKeyField(Organization, backref='accounts', null=True)
    organization_id: int  # Direct access to organization primary key
    email = peewee.CharField()
    status = peewee.CharField()   # ACTIVE, SUSPENDED or Closed
    budget_holder = peewee.ForeignKeyField(Person, backref="budget_holder", null=True)
    finance_code = peewee.CharField(null=True)
    task_code = peewee.CharField(null=True)
    creation_date: datetime.date = peewee.DateField(null=True)
    closure_date: datetime.date = peewee.DateField(null=True)
    is_recharged: bool = peewee.BooleanField(default=True)
    sysadmin: Iterable["Sysadmin"]  # backref
    notes: Iterable["Note"]  # backref
    transactions: Iterable["Transaction"]  # backref

    def get_transaction_details(self, start_date: datetime.date = None, end_date: datetime.date = None) -> list[dict]:
        """Returns a list of dicts describing MonthlyUsage and Transactions in the account between `start_date` and
        `end_date`.

        :param start_date: Include transactions that occur on or after this date. If None, defaults to
            Account.creation_date.
        :param end_date: Include transactions that occur on or before this date. If None, defaults to
            Account.final_date.
        """
        if not self.creation_date:
            return []

        if start_date is None:
            start_date = self.creation_date
        if end_date is None or end_date > self.final_date:
            end_date = self.final_date

        monthly_usage = self.get_monthly_usage(start_date, end_date)
        transaction_details = [monthly_usage.to_json() for monthly_usage in monthly_usage]
        transactions = self.get_transactions(start_date, end_date)
        transaction_details.extend([transaction.to_json() for transaction in transactions])

        transaction_details = self.calculate_running_total(transaction_details)

        return transaction_details

    @staticmethod
    def calculate_running_total(transaction_details: list[dict]) -> list[dict]:
        # sort transactions by date and add running total
        transaction_details = sorted(transaction_details, key=lambda d: d['date'])
        running_total = 0
        for row in transaction_details:
            running_total += row["gross_total_pound"]
            row["running_total"] = running_total
        return transaction_details

    def get_transactions(self, start_date: datetime.date, end_date: datetime.date) -> Iterable["Transaction"]:
        """Returns a list of Transactions between the account creation date and the account
        closure date"""
        # Join to RechargeRequest provides information given in Transaction.to_json method.
        transactions: Iterable[Transaction] = (
            Transaction.select(Transaction, RechargeRequest)
            .join(RechargeRequest, JOIN.LEFT_OUTER)
            .where((Transaction.account == self.id) & (Transaction.date >= start_date) & (Transaction.date <= end_date))
        )
        return transactions

    def get_monthly_usage(self, start_date: datetime.date, end_date: datetime.date) -> Iterable["MonthlyUsage"]:
        """Returns a list of dicts describing MonthlyUsage between `start_date` and `end_date`.

        :param start_date: The date after which to include monthly usage data.
        :param end_date: The date up to which to include monthly usage data.
        """
        required_months = aam.utilities.get_months_between(start_date, end_date)
        self.check_missing_monthly_transactions(required_months)

        # Join to Month and RechargeRequest is used by MonthlyUsage.to_json method
        usage: Iterable[MonthlyUsage] = (
            MonthlyUsage.select(MonthlyUsage, Month, RechargeRequest.reference)
            .join_from(MonthlyUsage, RechargeRequest, JOIN.LEFT_OUTER)
            .join_from(MonthlyUsage, Month)
            .where((MonthlyUsage.month_id.in_(required_months)) & (MonthlyUsage.account_id == self.id)))

        return usage

    def check_missing_monthly_transactions(self, required_months: list[int]):
        """Accounts should have a usage transaction for each month the account is open. This function checks if the
        account has 'monthly' type transactions for each month code in `required_months`."""
        usage: Iterable[MonthlyUsage] = (MonthlyUsage.select(MonthlyUsage.month_id)
                                         .where((MonthlyUsage.month_id.in_(required_months)) & (MonthlyUsage.account_id == self.id))
                                         )
        existing_transaction_months = [monthly_usage.month_id for monthly_usage in usage]
        missing_months = set(required_months) - set(existing_transaction_months)
        if missing_months:
            for month_code in missing_months:
                MonthlyUsage.create(account=self.id, month=month_code,
                                    date=aam.utilities.date_from_month_code(month_code))

    @property
    def final_date(self) -> datetime.date:
        """Return the final date on which the account is active."""
        if self.closure_date and self.closure_date <= datetime.date.today():
            return self.closure_date
        else:
            return datetime.date.today()

    def get_balance(self, date: datetime.date, inclusive: bool = True):
        """Get the balance of an account on a certain date.

        :param date: The date on which to calculate the balance.
        :param inclusive: Whether the balance includes or excludes transactions that fall on `date`.
        """
        if not inclusive:
            date = date - datetime.timedelta(days=1)

        transaction_details = self.get_transaction_details(end_date=date)
        if len(transaction_details) == 0:
            return 0
        return transaction_details[-1]["running_total"]


class Sysadmin(BaseModel):
    id = peewee.AutoField()
    person = peewee.ForeignKeyField(Person, backref="sysadmin")
    account = peewee.ForeignKeyField(Account, backref="sysadmin")

    @property
    def full_name(self) -> str:
        return f"{self.person.first_name} {self.person.last_name}"

class Note(BaseModel):
    id = peewee.AutoField()
    date = peewee.DateField()
    text = peewee.CharField()
    type = peewee.CharField()
    account = peewee.ForeignKeyField(Account, backref="notes")

class MonthlyUsage(BaseModel):
    # Usage is always in dollars
    id = peewee.AutoField()
    account = peewee.ForeignKeyField(Account, backref="monthly_usage")
    date: datetime.date = peewee.DateField()
    account_id: int  # Direct access to foreign key value
    amount: Decimal = peewee.DecimalField(null=True)  # The net value of the usage
    month: Month = peewee.ForeignKeyField(Month, backref="monthly_usage")
    month_id: int  # Direct access to foreign key value
    shared_charge: Decimal = peewee.DecimalField(default=0)
    recharge_request = peewee.ForeignKeyField(RechargeRequest, backref="monthly_usage", null=True)
    note = peewee.CharField(null=True)

    def to_json(self) -> dict:
        details = {"id": self.id, "account_id": self.account_id, "type": TRANSACTION_TYPES[self.type],
                   "date": self.date, "amount": self.amount, "shared_charge": self.shared_charge,
                   "support_charge": self.support_charge, "currency": "$", "gross_total_dollar": self.gross_total_dollar,
                   "gross_total_pound": self.gross_total_pound, "note": self.note}
        if self.recharge_request:
            details["reference"] = f"Recharge - {self.recharge_request.reference}"
        return details

    @property
    def type(self) -> int:
        return TRANSACTION_TYPES.index("Monthly Usage")

    @property
    def support_eligible(self) -> bool:
        """Accounts must pay 10% charge after 01/08/24 as this was when the OGVA started."""
        return self.date >= datetime.date(2024, 8, 1)

    @property
    def support_charge(self) -> Decimal:
        """If the transaction needs to be charged for support, return the amount in dollars."""
        if self.support_eligible and self.amount:
            return (self.amount + self.shared_charge) * Decimal(0.1)
        else:
            return Decimal(0)

    @property
    def gross_total_dollar(self) -> Decimal:
        """Usage + shared charges + support + VAT."""
        if self.amount:
            return (self.amount + self.shared_charge + self.support_charge) * Decimal(1.2)
        else:
            return Decimal(0)

    @property
    def gross_total_pound(self) -> Decimal:
        """Gross total in dollars multiplied by exchange rate."""
        if self.gross_total_dollar:
            return self.gross_total_dollar * self.month.exchange_rate
        else:
            return Decimal(0)

class Transaction(BaseModel):
    id = peewee.AutoField()
    account = peewee.ForeignKeyField(Account, backref="transactions")
    account_id: int  # Direct access to Foreign key value
    type: int = peewee.IntegerField()
    date: datetime.date = peewee.DateField()
    amount: Decimal = peewee.DecimalField(null=True)  # The net value of the transaction
    is_pound = peewee.BooleanField()
    exchange_rate: Decimal = peewee.DecimalField(null=True)   # USD/GBP
    recharge_request = peewee.ForeignKeyField(RechargeRequest, backref="transactions", null=True)
    note = peewee.CharField(null=True)
    reference = peewee.CharField(null=True)
    project_code = peewee.CharField(null=True)
    task_code = peewee.CharField(null=True)

    @property
    def support_eligible(self) -> bool:
        """Accounts must pay 10% charge after 01/08/24 as this was when the OGVA started."""
        return self.date >= datetime.date(2024, 8, 1)

    @property
    def support_charge(self) -> Decimal:
        if self.support_eligible and self.amount:
            if self.type == TRANSACTION_TYPES.index("Savings Plan"):
                return self.amount * Decimal(0.1)
        return Decimal(0)

    def to_json(self) -> dict:
        transaction_type = TRANSACTION_TYPES[self.type]
        transaction = {"id": self.id, "date": self.date, "account_id": self.account_id, "type": transaction_type,
                       "support_charge": self.support_charge, "note": self.note, "reference": self.reference,
                       "project_code": self.project_code, "task_code": self.task_code}
        if self.is_pound:
            # Accounts are settled in pounds so there is no reason to convert a pound transaction to a dollar value
            transaction.update({"currency": "£", "gross_total_pound": self.gross_total_pound})
        else:
            transaction.update({"currency": "$", "exchange_rate": self.exchange_rate, "amount": self.amount,
                                "gross_total_dollar": self.gross_total_dollar,
                                "gross_total_pound": self.gross_total_pound})

        if self.recharge_request:
            transaction["recharge_reference"] = self.recharge_request.reference
        else:
            transaction["recharge_reference"] = "-"
        return transaction

    @property
    def amount_pound(self) -> decimal.Decimal | None:
        """Return the net value of the transaction in pounds."""
        if not self.amount:
            return None
        if self.is_pound:
            return self.amount
        else:
            return self.amount * self.exchange_rate

    @property
    def amount_dollar(self) -> decimal.Decimal | None:
        """Return the net value of the transaction in dollars."""
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
    def gross_total_dollar(self) -> Decimal | None:
        """Calculate the total cost for the month, adding 20% for VAT."""
        if self.amount is None or self.amount_dollar is None:
            return None
        else:
            return (self.amount_dollar + self.support_charge) * Decimal(1.2)

    @property
    def gross_total_pound(self) -> Decimal | None:
        """Calculate the total cost of the transaction, converting from dollars."""
        if self.is_pound:
            return self.amount
        if self.gross_total_dollar is None:
            return None

        return  self.gross_total_dollar * self.exchange_rate


class SharedCharge(BaseModel):
    # Shared charges are a way to assign additional usage to a MonthlyUsage.
    id = peewee.AutoField()
    name = peewee.TextField()
    date: datetime.date = peewee.DateField()
    amount: decimal.Decimal = peewee.DecimalField()


class AccountJoinSharedCharge(BaseModel):
    account = peewee.ForeignKeyField(Account, backref="shared_charges_join")
    account_id: int  # Direct access to Foreign Key
    shared_charge = peewee.ForeignKeyField(SharedCharge, backref="account_join", on_delete="CASCADE")
    shared_charge_id: int # Direct access to Foreign Key

    class Meta:
        primary_key = peewee.CompositeKey('account', 'shared_charge')


db.create_tables([Account, LastAccountUpdate, Person, Sysadmin, Note, Month, MonthlyUsage, Transaction, RechargeRequest,
                  SharedCharge, AccountJoinSharedCharge, Organization])
