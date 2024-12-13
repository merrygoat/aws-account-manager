from decimal import Decimal
from typing import TYPE_CHECKING

from nicegui import ui

from aam.models import Account
from aam.utilities import date_picker


if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIImport:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent
        ui.html("Import data").classes("text-xl")
        with ui.row():
            self.label = ui.label("Import Month")
            self.import_date = ui.select(options=[])
        self.import_textbox = ui.textarea("Raw data")
        self.import_button = ui.button("Import data", on_click=self.import_billing)


    def import_billing(self):
        data = self.import_textbox.value
        if not data:
            ui.notify("No data to import.")
            return 0

        valid_account_numbers = [account.id for account in Account.select(Account.id)]

        data = data.split("\n")

        # Check data validity
        for index, line in enumerate(data):
            line = line.split(",")
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
            except:
                ui.notify(f"Malformed bill amount on line {index}")
                return 0
        ui.notify("Nice data.")