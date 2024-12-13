import calendar
import datetime
import decimal
from decimal import Decimal
from typing import TYPE_CHECKING

from nicegui import ui

from aam.models import Account, Month, Bill

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIImport:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent
        ui.html("Import data").classes("text-xl")
        with ui.grid(columns="auto auto").classes("place-items-center gap-1"):
            self.label = ui.label("Month")
            self.label = ui.label("Year")
            self.month = ui.select(options={index + 1: month for index, month in enumerate(calendar.month_abbr[1:])}).props("outlined dense").classes("min-w-[120px]")
            self.year = ui.select(options=list(range(2021, datetime.date.today().year + 1))).props("outlined dense").classes("min-w-[120px]")
        self.import_textbox = ui.textarea("Raw data").props("outlined").classes("w-1/2")
        self.import_button = ui.button("Import data", on_click=self.import_billing)


    def import_billing(self):
        data = self.import_textbox.value
        if not data:
            ui.notify("No data to import.")
            return 0
        data = data.split("\n")

        valid_account_numbers = [account.id for account in Account.select(Account.id)]

        # Check data validity
        for index, line in enumerate(data):
            # Remove all spaces
            line = line.replace(" ", "")
            # No usage can be represented by a dash
            line = line.replace("-", "0")
            # Replace the field separator comma with a rearely used character
            line = line.replace(",", "@", 1)
            # Remove any thousand or million separators in usage amount
            line = line.replace(",", "")
            # Split the line by field seperator
            line = line.split("@")
            data[index] = line
            if len(line) != 2:
                ui.notify(f"Malformed data on line {index}.")
                return 0
            if len(line[0]) != 12:
                ui.notify(f"Malformed account number on line {index}")
                return 0
            if line[0] not in valid_account_numbers:
                ui.notify(f"Account number {line[0]} at line {index} not found in database.")
                return 0
            try:
                Decimal(line[1])
            except decimal.InvalidOperation:
                ui.notify(f"Malformed bill amount on line {index}")
                return 0
        ui.notify("Data is valid.")

        month = self.month.value
        year = self.year.value
        month_code = (year * 12 + month)
        month = Month.get(month_code=month_code)

        for line in data:
            bill = Bill.get_or_create(account_id=line[0], month=month.id)[0]
            bill.usage = decimal.Decimal(line[1])
            bill.save()
        self.parent.bills.update_bill_grid()
        ui.notify("Bills added to accounts.")