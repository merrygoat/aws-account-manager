import datetime
import decimal
from typing import TYPE_CHECKING
import re

import nicegui.events
from nicegui import ui

import aam.utilities
from aam.models import Account, Month, Transaction, Person, Sysadmin
from aam.utilities import month_select, year_select

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIImport:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent
        ui.html("Import data").classes("text-xl")
        self.import_type = ui.select({1: "Transaction Data - One month", 2:"Transaction Data - One account", 3:"Exchange Rate", 4:"Account Details"}, label="Import Type", value=1,
                                     on_change=self.import_type_selected)
        self.description = ui.label("")
        with ui.grid(columns="auto auto").classes("place-items-center gap-1") as self.date_pick_grid:
            ui.label("Month")
            ui.label("Year")
            self.month = month_select()
            self.year = year_select()
        self.gross_toggle = ui.radio(["Net", "Gross"], value="Net").props('inline')
        self.import_textbox = ui.textarea("Raw data").classes("w-1/2")
        self.import_button = ui.button("Import data", on_click=self.import_data)

        self.gross_toggle.set_visibility(False)

    'Data must be in the format: "account number, transaction amount" with one account per line. '
    'Comma is the only valid field separator.'

    def import_type_selected(self, event: nicegui.events.ValueChangeEventArguments):
        import_type = event.sender.value
        if import_type == 1:
            self.description.text = ('Data must be in the format: "account number, transaction amount" with one account '
                                     'per line. Comma or tab can be use as field separators.')
            self.date_pick_grid.set_visibility(True)
            self.gross_toggle.set_visibility(False)
        elif import_type == 2:
            self.description.text = ('Data must be tab delimited in the format, "Month-year   amount ($)", with one '
                                     'month per line and the account number on its own on the first line.')
            self.date_pick_grid.set_visibility(False)
            self.gross_toggle.set_visibility(True)
        elif import_type == 3:
            self.description.text = ('Data must be in the format, "Month-year, exchange_rate", with one month per line.'
                                     'e.g "Mar-23, 0.756473".')
            self.date_pick_grid.set_visibility(False)
            self.gross_toggle.set_visibility(False)
        elif import_type == 4:
            self.description.text = ('Data must be in the format, "Account Number, Account Name, Budget holder Name, '
                                     'Budgetholder email, Sysadmin Name, Sysadmin Email, Finance Code, Task Code", '
                                     'with one account per line.')
            self.date_pick_grid.set_visibility(False)
            self.gross_toggle.set_visibility(False)

    def import_data(self, event: nicegui.events.ClickEventArguments):
        data = self.import_textbox.value
        if not data:
            ui.notify("No data to import.")
            return 0

        import_type = self.import_type.value
        if import_type == 1:
            self.import_month_transactions(data)
        if import_type == 2:
            self.import_account_transactions(data)
        elif import_type == 3:
            self.import_exchange_rate(data)
        elif import_type == 4:
            self.import_account_details(data)

    def import_exchange_rate(self, data: str):
        data = data.split("\n")

        for index, line in enumerate(data):
            line = line.replace(" ", "")
            line = line.split(",")
            date = datetime.datetime.strptime(line[0], "%b-%y").date()
            try:
                exchange_rate = decimal.Decimal(line[1])
            except decimal.InvalidOperation:
                ui.notify(f"Malformed exchange rate on line {index}")
                return 0
            month_code = aam.utilities.month_code(date.year, date.month)
            month = Month.get_or_none(month_code=month_code)
            if month is None:
                Month.create(month_code=month_code, exchange_rate=exchange_rate)
            month.exchange_rate = exchange_rate
            month.save()
        self.parent.settings.ui_exchange_rate.populate_exchange_rate_grid()
        ui.notify("Exchange rates imported.")

    def import_month_transactions(self, data: str):
        data = data.split("\n")

        valid_account_numbers = [account.id for account in Account.select(Account.id)]

        processed_lines = []

        # Check data validity
        for index, line in enumerate(data):
            # Remove all spaces
            line = line.replace(" ", "")
            # If the line is blank then skip it
            if line == "":
                continue
            # Remove dollar signs
            line = line.replace("$", "")
            # No usage can be represented by a dash
            line = line.replace("-", "0")
            # Remove any thousand or million separators in usage amount
            line = re.sub(",(?=\d{3})", "", line)
            # Any other commas are now delimiters so replace them with tabs
            line = line.replace(",", "\t")
            # Split the line by field seperator
            line = line.split("\t")
            if len(line) not in [2, 3]:
                ui.notify(f"Malformed data on line {index} - wrong number of fields.")
                return 0
            if len(line[0]) != 12:
                ui.notify(f"Malformed account number on line {index + 1} - must be 12 characters")
                return 0
            if line[0] not in valid_account_numbers:
                ui.notify(f"Account number {line[0]} at line {index + 1} not found in database.")
                return 0
            try:
                decimal.Decimal(line[-1])
            except decimal.InvalidOperation:
                ui.notify(f"Malformed transaction amount on line {index + 1} - unable to convert to Decimal")
                return 0
            processed_lines.append(line)
        ui.notify("Data is valid.")

        month = self.month.value
        year = self.year.value
        date = datetime.date(year, month, 1)

        for line in processed_lines:
            transaction = Transaction.get_or_none(account=line[0], type="Monthly", date=date)
            if transaction:
                transaction.amount = decimal.Decimal(line[-1])
                transaction.save()
            else:
                Transaction.create(account=line[0], type="Monthly", date=date, amount=decimal.Decimal(line[-1]),
                                   is_pound=False)

        self.parent.transactions.update_transaction_grid()
        ui.notify("Transactions added to accounts.")

    def import_account_transactions(self, data: str):
        data = data.split("\n")

        valid_account_numbers = [account.id for account in Account.select(Account.id)]

        account_number = data.pop(0)
        if len(account_number) != 12:
            ui.notify(f"Malformed account number on line 1 - must be 12 characters")
            return 0
        if account_number not in valid_account_numbers:
            ui.notify(f"Account number {account_number} at line 1 not found in database.")
            return 0

        # Check all lines for validity before adding anything to the database.
        processed_lines = []
        for index, line in enumerate(data):
            # Ignore any blank lines
            if not line:
                continue
            line = line.split("\t")
            # Remove any thousands comma delimiters
            line[1] = line[1].replace(",", "")
            try:
                datetime.datetime.strptime(line[0], "%b-%y").date()
            except ValueError:
                ui.notify(f"Malformed date on line {index + 1}")
                return 0
            try:
                decimal.Decimal(line[1])
            except decimal.InvalidOperation:
                ui.notify(f"Malformed amount on line {index + 1}")
                return 0
            processed_lines.append(line)

        for line in processed_lines:
            date = datetime.datetime.strptime(line[0], "%b-%y").date()
            amount = decimal.Decimal(line[1])

            transaction = Transaction.get_or_none(account=account_number, date=date, type="Monthly")
            if not transaction:
                Transaction.create(account=account_number, date=date, type="Monthly", amount=amount, is_pound=False)
            else:
                if self.gross_toggle.value == "Gross":
                    amount = (amount / decimal.Decimal(1.2))
                transaction.amount = amount
                transaction.save()
        # If the account being imported to is currently visible then update the transactions grid.
        if self.parent.get_selected_account_id() == account_number:
            self.parent.transactions.update_transaction_grid()
        ui.notify("Transactions added.")

    @staticmethod
    def import_account_details(data: str):
        data = data.split("\n")

        valid_account_numbers = [account.id for account in Account.select(Account.id)]

        processed_lines = []

        for index, line in enumerate(data):
            line = line.split("\t")
            if not line:
                continue
            if not line[0]:
                continue
            if len(line[0]) != 12:
                ui.notify(f"Malformed account number on line {index + 1} - must be 12 characters")
                return 0
            if line[0] not in valid_account_numbers:
                ui.notify(f"Account number {line[0]} at line {index + 1} not found in database.")
                return 0
            processed_lines.append(line)

        for line in processed_lines:
            account_id = line[0]
            account_name = line[1]
            budget_holder_name = line[2].split()
            budget_holder_email = line[3]
            sysadmin_name = line[4].split()
            sysadmin_email = line[5]
            finance_code = line[6]
            task_code = line[7]
            account: Account = Account.get(Account.id==account_id)
            account.name = account_name
            account.finance_code = finance_code
            account.task_code = task_code

            if budget_holder_name:
                budget_holder = Person.get_or_create(first_name=budget_holder_name[0], last_name=budget_holder_name[1],
                                                     email=budget_holder_email)[0]
                account.budget_holder = budget_holder.id
            else:
                account.budget_holder = None

            for sysadmin in account.sysadmin:
                sysadmin.delete_instance()
            if sysadmin_name:
                sysadmin = Person.get_or_create(first_name=sysadmin_name[0], last_name=sysadmin_name[1],
                                                email=sysadmin_email)[0]
                Sysadmin.create(account=account_id, person=sysadmin.id)

            account.save()
        ui.notify("Account details imported.")