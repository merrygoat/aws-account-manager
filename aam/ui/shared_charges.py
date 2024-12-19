import re
from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

from aam.models import SharedCharge, Account
from aam.utilities import month_select, year_select

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UISharedCharges:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        self.add_shared_charge_dialog = UINewSharedChangeDialog(self)

        ui.html("Shared Charges").classes("text-2xl")
        with ui.row().classes("w-full no-wrap"):
            with ui.column().classes('w-1/2'):
                self.shared_charges_table = ui.aggrid({
                    'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                                   {"headerName": "Name", "field": "name"},
                                   {"headerName": "Amount", "field": "amount"},
                                   {"headerName": "Num Accounts", "field": "recharge_amount"}],
                    'rowData': {}
                })
                self.new_charge_button = ui.button("New Shared Charge", on_click=self.add_shared_charge_dialog.open)
            with ui.column().classes('w-1/2'):
                with ui.grid(columns="auto auto"):
                    ui.label("Name")
                    self.name = ui.input()
                    ui.label("Amount")
                    self.amount = ui.input()
                    ui.label("Accounts")
                    self.accounts = ui.select(options=[])
                    self.save_changes = ui.button("Save Changes", on_click=self.save_changes)


        self.populate_shared_charges_table()

    def save_changes(self, event: nicegui.events.ClickEventArguments):
        pass

    def populate_shared_charges_table(self):
        shared_charges = SharedCharge.select()
        shared_charges = [charge.to_dict for charge in shared_charges]
        self.shared_charges_table.options["rowData"] = shared_charges
        self.shared_charges_table.update()


class UINewSharedChangeDialog:
    def __init__(self, parent: UISharedCharges):
        self.parent = parent

        self.accounts = []

        with ui.dialog() as self.dialog:
            with ui.card():
                ui.html("Add New Shared Charge").classes("text-2xl")
                with ui.grid(columns="auto auto"):
                    ui.label("Name")
                    self.name = ui.input()
                    ui.label("Month")
                    self.month = month_select()
                    ui.label("Year")
                    self.year = year_select()
                    ui.label("Amount ($)")
                    self.amount = ui.input(validation=lambda value: 'Invalid format' if re.fullmatch(r"\d*.\d*", value) is None else None)
                    ui.label("Accounts")
                    self.account_select = ui.select([], multiple=True).classes("min-w-[400px]").props('popup-content-class="!max-h-[500px]"')
                with ui.row().classes("w-full"):
                    ui.label("Show suspended accounts")
                    self.show_suspended = ui.checkbox(on_change=self.update_account_select, value=False)
                    ui.label("Show closed accounts")
                    self.show_closed = ui.checkbox(on_change=self.update_account_select, value=False)
                with ui.row():
                    ui.button("Save Changes")
                    ui.button("Cancel", on_click=self.dialog.close)
            self.update_account_select()

    def update_account_select(self):
        status = ["ACTIVE"]
        if self.show_suspended.value:
            status.append("SUSPENDED")
        if self.show_closed.value:
            status.append("Closed")
        accounts = Account.select().where(Account.status.in_(status))
        accounts = {account.id: account.name for account in accounts}
        self.account_select.set_options(accounts)

    def open(self):
        self.dialog.open()
