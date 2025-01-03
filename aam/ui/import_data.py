import datetime
import decimal
from typing import TYPE_CHECKING
import re

import nicegui.events
from nicegui import ui

import aam.utilities
from aam.models import Account, Month, Bill
from aam.utilities import month_select, year_select

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIImport:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent
        ui.html("Import data").classes("text-xl")
        self.import_type = ui.select({1: "Billing Data", 2:"Exchange Rate"}, label="Import Type", value=1,
                                     on_change=self.import_type_selected)
        self.description = ui.label("")
        with ui.grid(columns="auto auto").classes("place-items-center gap-1") as self.date_pick_grid:
            ui.label("Month")
            ui.label("Year")
            self.month = month_select()
            self.year = year_select()
        self.import_textbox = ui.textarea("Raw data").classes("w-1/2")
        self.import_button = ui.button("Import data", on_click=self.import_data)

    'Data must be in the format: "account number, bill amount" with one account per line. '
    'Comma is the only valid field separator.'

    def import_type_selected(self, event: nicegui.events.ValueChangeEventArguments):
        selected_person = event.sender.value
        if selected_person == 1:
            self.description = ('Data must be in the format: "account number, bill amount" with one account per line. '
                                'Comma is the only valid field separator.')
            self.date_pick_grid.set_visibility(True)
        elif selected_person == 2:
            self.description = ('Data must be in the format, "Month-year, exchange_rate, with one month per line.'
                                'e.g "Mar-23, 0.756473".')
            self.date_pick_grid.set_visibility(False)

    def import_data(self, event: nicegui.events.ClickEventArguments):
        import_type = self.import_type.value
        if import_type == 1:
            self.import_billing()
        elif import_type == 2:
            self.import_exchange_rate()

    def import_exchange_rate(self):
        data = self.import_textbox.value
        if not data:
            ui.notify("No data to import.")
            return 0
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

    def import_billing(self):
        data = self.import_textbox.value
        if not data:
            ui.notify("No data to import.")
            return 0
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
                ui.notify(f"Malformed account number on line {index} - must be 12 characters")
                return 0
            if line[0] not in valid_account_numbers:
                ui.notify(f"Account number {line[0]} at line {index} not found in database.")
                return 0
            try:
                decimal.Decimal(line[-1])
            except decimal.InvalidOperation:
                ui.notify(f"Malformed bill amount on line {index} - unable to convert to Decimal")
                return 0
            processed_lines.append(line)
        ui.notify("Data is valid.")

        month = self.month.value
        year = self.year.value
        month_code = aam.utilities.month_code(year, month)
        month = Month.get(month_code=month_code)

        for line in processed_lines:
            bill = Bill.get_or_create(account=line[0], month=month.id)[0]
            bill.usage = decimal.Decimal(line[-1])
            bill.save()
        self.parent.bills.update_bill_grid()
        ui.notify("Bills added to accounts.")