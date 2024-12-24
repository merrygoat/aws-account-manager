import decimal
import re
from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

from aam.models import SharedCharge, Account, Month, AccountJoinSharedCharge
from aam.utilities import month_select, year_select, month_code

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UISharedCharges:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        self.add_shared_charge_dialog = UINewSharedChangeDialog(self)

        ui.html("Shared Charges").classes("text-2xl")
        with ui.row().classes("w-full no-wrap"):
            with ui.column().classes('w-2/3'):
                self.shared_charges_table = ui.aggrid({
                    'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                                   {"headerName": "Name", "field": "name"},
                                   {"headerName": "Month", "field": "month", 'sort': 'asc'},
                                   {"headerName": "Amount", "field": "amount"},
                                   {"headerName": "Accounts", "field": "account_names"}],
                    'rowData': {},
                    'rowSelection': "single",
                    'autoSizeStrategy': {
                        'type': 'fitCellContents'
                    }
                })
                with ui.row():
                    self.new_charge_button = ui.button("New Shared Charge", on_click=self.add_shared_charge_dialog.open)
                    self.delete_selected_button = ui.button("Delete Selected Shared Charge", on_click=self.delete_selected)

        self.populate_shared_charges_table()

    def save_changes(self, event: nicegui.events.ClickEventArguments):
        pass

    async def delete_selected(self, event: nicegui.events.ClickEventArguments):
        selected_row = await self.shared_charges_table.get_selected_row()
        if selected_row is None:
            ui.notify("No shared charge selected.")
            return 0
        else:
            shared_charge = SharedCharge.get(SharedCharge.id==selected_row["id"])
            shared_charge.delete_instance()
            self.populate_shared_charges_table()
            ui.notify("Shared charge deleted.")

    def populate_shared_charges_table(self):
        shared_charges = SharedCharge.select()
        shared_charges = [charge.to_dict() for charge in shared_charges]
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
                    ui.button("Save Changes", on_click=self.create_new_shared_charge)
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

    def create_new_shared_charge(self, event: nicegui.events.ClickEventArguments):
        if self.name == "":
            ui.notify("Name must be provided.")
            return 0

        try:
            amount = decimal.Decimal(self.amount.value)
        except decimal.InvalidOperation:
            ui.notify("Amount is not a valid number.")
            return 0

        month = Month.get(month_code=month_code(self.year.value, self.month.value))
        shared_charge = SharedCharge.create(name=self.name.value, amount=amount, month_id=month.id)
        for account_id in self.account_select.value:
            AccountJoinSharedCharge.create(account_id=account_id, shared_charge_id=shared_charge.id)
        self.parent.populate_shared_charges_table()
        self.close()
        ui.notify("New shared charge added.")

    def open(self):
        self.dialog.open()

    def close(self):
        self.dialog.close()
