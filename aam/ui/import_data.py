import datetime
import decimal
from typing import TYPE_CHECKING
import re

import nicegui.events
from nicegui import ui

import aam.utilities
from aam.models import Account, Month, Person, Sysadmin, MonthlyUsage, TRANSACTION_TYPES, Transaction
from aam.utilities import month_select, year_select

if TYPE_CHECKING:
    from aam.ui.main import UIMainForm


class UIImport:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent
        ui.html("Import data").classes("text-xl")
        self.import_type = ui.select({1: "Monthly Usage - One month, multiple account", 2:"Monthly usage - One account, multiple months", 3:"Exchange Rate", 4:"Account Details", 5: "Transactions"},
                                     label="Import Type", value=1, on_change=self.import_type_selected)
        self.description = ui.label("").style('white-space: pre-wrap')
        with ui.grid(columns="auto auto").classes("place-items-center gap-1") as self.date_pick_grid:
            ui.label("Month")
            ui.label("Year")
            self.month = month_select()
            self.year = year_select()
        self.import_textbox = ui.textarea("Raw data").classes("w-1/2")
        self.import_button = ui.button("Import data", on_click=self.import_data)


    'Data must be in the format: "account number, transaction amount" with one account per line. '
    'Comma is the only valid field separator.'

    def import_type_selected(self, event: nicegui.events.ValueChangeEventArguments):
        import_type = event.sender.value
        if import_type == 1:
            self.description.text = ('Data must be in the format: "account number, transaction amount" with one account '
                                     'per line. Comma or tab can be use as field separators.')
            self.date_pick_grid.set_visibility(True)
        elif import_type == 2:
            self.description.text = ('Data must be tab delimited in the format, "Month-year   amount ($)", with one '
                                     'month per line and the account number on its own on the first line.\n'
                                     'Data before 01/07/24 is imported as gross values and after this date as net '
                                     'values.'
                                     )
            self.description.text = ()
            self.date_pick_grid.set_visibility(False)
        elif import_type == 3:
            self.description.text = ('Data must be in the format, "Month-year, exchange_rate", with one month per line.'
                                     'e.g "Mar-23, 0.756473".')
            self.date_pick_grid.set_visibility(False)
        elif import_type == 4:
            self.description.text = ('Data must be in the format, "Account Number, Account Name, Budget holder Name, '
                                     'Budgetholder email, Sysadmin Name, Sysadmin Email, Finance Code, Task Code,'
                                     ' Creation Date (YYYY-MM-DD)", with one account per line.')
            self.date_pick_grid.set_visibility(False)
        elif import_type == 5:
            self.description.text = ('Data must be in the format, "Transaction reference, Transaction Date, AWS account Name, '
                                     'Transaction Type, Note, Finance Code, Task Code, amount", with one transaction per line.')
            self.date_pick_grid.set_visibility(False)

    def import_data(self, event: nicegui.events.ClickEventArguments):
        data = self.import_textbox.value
        if not data:
            ui.notify("No data to import.")
            return 0

        import_type = self.import_type.value
        if import_type == 1:
            self.import_month_usage(data)
        if import_type == 2:
            self.import_account_monthly_usage(data)
        elif import_type == 3:
            self.import_exchange_rate(data)
        elif import_type == 4:
            self.import_account_details(data)
        elif import_type == 5:
            self.import_transactions(data)

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

    def import_month_usage(self, data: str):
        data = data.split("\n")

        valid_account_numbers = [account.id for account in Account.select(Account.id)]

        processed_lines = []

        if not self.month.value:
            ui.notify("Must select month.")
            return 0

        if not self.year.value:
            ui.notify("Must select year.")
            return 0

        # Check data validity
        # Assumes account number is first field and amount is last field. Optional account name inbetween.
        for index, line in enumerate(data):
            # Remove all spaces
            line = line.replace(" ", "")
            # Remove any trailing commas
            line = line.rstrip(",")
            # If the line is blank then skip it
            if line == "":
                continue
            # Remove dollar signs
            line = line.replace("$", "")
            # Remove any thousand or million separators in usage amount
            line = re.sub("\d,(?=\d{3})", "", line)
            # Any other commas are now delimiters so replace them with tabs
            line = line.replace(",", "\t")
            # Split the line by field seperator
            line = line.split("\t")
            # No usage can be represented by a dash
            line[-1] = line[-1].replace("-", "0")
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
                ui.notify(f"Malformed usage amount on line {index + 1} - unable to convert to Decimal")
                return 0
            processed_lines.append(line)
        ui.notify("Data is valid.")

        month_code = aam.utilities.month_code(self.year.value, self.month.value)

        for line in processed_lines:
            usage = MonthlyUsage.get_or_none(account=line[0], month=month_code)
            if usage:
                usage.amount = decimal.Decimal(line[-1])
                usage.save()
            else:
                MonthlyUsage.create(account=line[0], month=month_code, amount=decimal.Decimal(line[-1]),
                                    date=aam.utilities.date_from_month_code(month_code))

        self.parent.transactions.update_transaction_grid()
        ui.notify("Monthly Usage added to accounts.")

    def import_account_monthly_usage(self, data: str):
        """Import multiple months of data for one or more accounts."""
        data = data.split("\n")

        valid_account_numbers = [account.id for account in Account.select(Account.id)]

        account_numbers = data.pop(0).split("\t")
        num_columns = len(account_numbers)

        # Go through the account numbers checking their validity
        # Skip the first value as it is a label
        for index in range(1, len(account_numbers)):
            account_number = account_numbers[index]
            if len(account_number) != 12:
                ui.notify(f"Malformed account number '{account_number}', on line 1, column {index + 2} - must be 12 digits")
                return 0
            if account_number not in valid_account_numbers:
                ui.notify(f"Account number '{account_number}' at line 1, column {index + 2} not found in database.")
                return 0

        # Check all lines for validity before adding anything to the database.
        processed_lines = []
        for line_number, line in enumerate(data):
            # Ignore any blank lines
            if not line:
                continue
            # Remove any dollar symbols
            line = line.replace("$", "")
            # Remove any thousands comma delimiters
            line = line.replace(",", "")
            # Split line
            line = line.split("\t")
            # Check that the number of values in the line matches the number of columns in the header
            if len(line) != num_columns:
                ui.notify(f"Number of columns in line: {line_number + 2} does not match number of columns in header line.")
                return 0
            # Check that the date in the first column can be parsed
            try:
                datetime.datetime.strptime(line[0], "%b-%y").date()
            except ValueError:
                ui.notify(f"Malformed date on line {line_number + 2}")
                return 0
            # Go through the values in the row checking they can be parsed as numbers
            for column_index in range(1, num_columns):
                if line[column_index] != "-":
                    try:
                        decimal.Decimal(line[column_index])
                    except decimal.InvalidOperation:
                        ui.notify(f"Malformed amount '{line[column_index]}' on line {line_number + 2}, column {column_index + 1}")
                        return 0
            processed_lines.append(line)

        for line in processed_lines:
            date = datetime.datetime.strptime(line[0], "%b-%y").date()
            month_code = aam.utilities.month_code(date.year, date.month)
            for column_index in range(1, num_columns):
                account_number = account_numbers[column_index]
                # Skip if usage is a hyphen as this indicates that the account was not open at that time
                if line[column_index] == "-":
                    continue
                amount = decimal.Decimal(line[column_index])
                # AWS data from the API comes as gross totals while the breakdowns from Strategic Blue are net.
                if date < datetime.date(2024, 7, 1):
                    amount = (amount / decimal.Decimal(1.2))

                usage = MonthlyUsage.get_or_none(account=account_number, month=month_code)

                if not usage:
                    MonthlyUsage.create(account=account_number, month=month_code, amount=amount,
                                        date=aam.utilities.date_from_month_code(month_code))
                else:
                    usage.amount = amount
                    usage.save()
        # If the account being imported to is currently visible then update the transactions grid.
        if self.parent.get_selected_account_id() in account_numbers:
            self.parent.transactions.update_transaction_grid()
        ui.notify("Monthly Usage added.")

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
            account_opened = line[8]
            account: Account = Account.get(Account.id==account_id)
            account.name = account_name
            account.finance_code = finance_code
            account.task_code = task_code
            account.creation_date = datetime.date.fromisoformat(account_opened)

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

    # noinspection PyTypeChecker
    def import_transactions(self, data: str):
        data = data.split("\n")
        valid_account_names = [account.name for account in Account.select(Account.name)]

        processed_lines = []
        for index, line in enumerate(data):
            # Skip blank lines
            if not line:
                continue
            # Split the line by tab delimiter
            line = line.split("\t")
            # Remove any pound signs or thousands commas from the amount
            line[7] = line[7].replace("£", "")
            line[7] = line[7].replace(",", "")
            line[1] = datetime.datetime.strptime(line[1], "%d/%m/%Y").date()
            if line[2] not in valid_account_names:
                ui.notify(f"Account name '{line[2]}' on line {index + 1} not found in database.")
                return 0
            if line[3] not in TRANSACTION_TYPES:
                ui.notify(f"Transaction type '{line[3]}' on line {index + 1} not in valid transaction types: '{TRANSACTION_TYPES}'.")
                return 0
            try:
                # Amount is negative because it is a credit to the account
                line[7] = -decimal.Decimal(line[7])
            except decimal.InvalidOperation:
                ui.notify(
                    f"Malformed amount '{line[7]}' on line {index + 1}")
                return 0
            processed_lines.append(line)

        for line in processed_lines:
            account_id = Account.get(Account.name == line[2]).id
            transaction_type = TRANSACTION_TYPES.index(line[3])
            Transaction.create(account=account_id, date=line[1], amount=line[7], type=transaction_type,  is_pound=True, note=line[4],
                               reference=line[0], project_code=line[5], task_code=line[6])

        self.parent.transactions.update_transaction_grid()
        ui.notify("Transactions added.")
