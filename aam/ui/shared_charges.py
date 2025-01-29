import decimal
import re
from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

from aam.models import SharedCharge, Account, Month, AccountJoinSharedCharge
from aam.utilities import month_select, year_select, month_code, month_to_string

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UISharedCharges:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        self.shared_charge_dialog = UISharedChargeDialog(self)

        ui.html("Shared Charges").classes("text-2xl")
        with ui.row().classes("w-full no-wrap"):
            with ui.column().classes('w-2/3'):
                ui.label("Values are net values and do not include the support percentage. "
                         "VAT and the support charge are added automatically in the transaction tab.")
                self.shared_charges_table = ui.aggrid({
                    'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                                   {"headerName": "Name", "field": "name"},
                                   {"headerName": "Month", "field": "month", 'sort': 'asc', 'valueFormatter': 'value ? ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][new Date(value).getMonth()] + "-" + new Date(value).getFullYear() : "N/A"'},
                                   {"headerName": "Amount ($)", "field": "amount"},
                                   {"headerName": "Accounts", "field": "account_names"}],
                    'rowData': {},
                    'rowSelection': "single",
                    'autoSizeStrategy': {
                        'type': 'fitCellContents'
                    }
                })
                with ui.row():
                    self.new_charge_button = ui.button("New Shared Charge", on_click=self.add_new_shared_charge)
                    self.edit_selected_button = ui.button("Edit Selected Shared Charge", on_click=self.edit_selected)
                    self.duplicate_selected_button = ui.button("Duplicate Selected Shared Charge", on_click=self.duplicate_selected)
                    self.delete_selected_button = ui.button("Delete Selected Shared Charge", on_click=self.delete_selected)

        self.populate_shared_charges_table()

    def add_new_shared_charge(self, event: nicegui.events.ClickEventArguments):
        self.shared_charge_dialog.header.set_text("Add New Shared Charge")
        self.shared_charge_dialog.open(mode="new")

    async def edit_selected(self, event: nicegui.events.ClickEventArguments):
        selected_row = await self.shared_charges_table.get_selected_row()
        if selected_row is None:
            ui.notify("No shared charge selected to edit.")
        else:
            shared_charge = SharedCharge.get(SharedCharge.id==selected_row["id"])
            self.shared_charge_dialog.header.set_text("Editing existing Shared Charge")
            self.shared_charge_dialog.open(shared_charge, mode="edit")

    async def duplicate_selected(self, event: nicegui.events.ClickEventArguments):
        selected_row = await self.shared_charges_table.get_selected_row()
        if selected_row is None:
            ui.notify("No shared charge selected to duplicate.")
        else:
            shared_charge = SharedCharge.get(SharedCharge.id == selected_row["id"])
            self.shared_charge_dialog.header.set_text("Add New Shared Charge")
            self.shared_charge_dialog.open(shared_charge, mode="duplicate")

    async def delete_selected(self, event: nicegui.events.ClickEventArguments):
        selected_row = await self.shared_charges_table.get_selected_row()
        if selected_row is None:
            ui.notify("No shared charge selected.")
        else:
            shared_charge = SharedCharge.get(SharedCharge.id==selected_row["id"])
            shared_charge.delete_instance()
            self.populate_shared_charges_table()
            ui.notify("Shared charge deleted.")

    def populate_shared_charges_table(self):
        shared_charges = SharedCharge.select().where(SharedCharge.organization == self.parent.get_selected_organization_id())
        shared_charges = [charge.to_dict() for charge in shared_charges]
        self.shared_charges_table.options["rowData"] = shared_charges
        self.shared_charges_table.update()


class UISharedChargeDialog:
    def __init__(self, parent: UISharedCharges):
        self.parent = parent

        self.shared_charge_id: int | None = None

        with ui.dialog() as self.dialog:
            with ui.card():
                self.header = ui.label("").classes("text-2xl")
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
                    ui.button("Save Changes", on_click=self.save_shared_charge)
                    ui.button("Cancel", on_click=self.dialog.close)

    def update_account_select(self):
        selected_org_id = self.parent.parent.get_selected_organization_id()
        if not selected_org_id:
            return 0
        status = ["ACTIVE"]
        if self.show_suspended.value:
            status.append("SUSPENDED")
        if self.show_closed.value:
            status.append("Closed")
        accounts = Account.select().where((Account.status.in_(status)) & (Account.organization==selected_org_id))
        accounts = {account.id: account.name for account in accounts}
        self.account_select.set_options(accounts)

    def save_shared_charge(self, event: nicegui.events.ClickEventArguments):
        if self.name == "":
            ui.notify("Name must be provided.")
            return 0

        try:
            amount = decimal.Decimal(self.amount.value)
        except decimal.InvalidOperation:
            ui.notify("Amount is not a valid number.")
            return 0

        month = Month.get(month_code=month_code(self.year.value, self.month.value))

        if self.shared_charge_id:
            # Get existing SharedCharge and the accounts to which it applies
            shared_charge = SharedCharge.get(SharedCharge.id == self.shared_charge_id)
            accounts = (Account.select(Account.id).where(SharedCharge.id == self.shared_charge_id)
                        .join(AccountJoinSharedCharge)
                        .join(SharedCharge).dicts())
            account_ids = [account["id"] for account in accounts]
            ids_to_add = set(self.account_select.value) - set(account_ids)
            ids_to_delete = set(account_ids) - set(self.account_select.value)

            # Add any newly selected accounts
            for account_id in ids_to_add:
                AccountJoinSharedCharge.create(account=account_id, shared_charge=shared_charge.id)

            # Delete any accounts no longer selected
            (AccountJoinSharedCharge.delete()
             .where((AccountJoinSharedCharge.account.in_(ids_to_delete)) & (AccountJoinSharedCharge.shared_charge == shared_charge.id))
             .execute())

            shared_charge.name = self.name.value
            shared_charge.amount_pound = amount
            shared_charge.month = month.month_code
            shared_charge.save()
        else:
            shared_charge = SharedCharge.create(name=self.name.value, amount=amount, month=month.month_code,
                                                organization=self.parent.parent.get_selected_organization_id())
            for account_id in self.account_select.value:
                AccountJoinSharedCharge.create(account=account_id, shared_charge=shared_charge.id)

        self.parent.populate_shared_charges_table()
        self.parent.parent.transactions.update_transaction_grid()
        if self.shared_charge_id:
            ui.notify("Shared charge edited.")
        else:
            ui.notify("New shared charge added.")
        self.close()

    def open(self, shared_charge: SharedCharge | None = None, mode: str = "new"):
        # Possible modes are "new", "edit" or "duplicate"

        self.update_account_select()

        if mode == "edit":
            self.shared_charge_id = shared_charge.id

        if mode != "new":
            month = Month.get(Month.month_code == shared_charge.month)
            accounts = (Account.select(Account.id).where(SharedCharge.id == shared_charge.id)
                           .join(AccountJoinSharedCharge)
                           .join(SharedCharge).dicts())
            account_ids = [account["id"] for account in accounts]

            self.name.value = shared_charge.name
            self.month.value = month.month
            self.year.value = month.year
            self.amount.value = str(shared_charge.amount)
            self.account_select.value = account_ids

        self.dialog.open()

    def close(self):
        self.shared_charge_id = None
        self.dialog.close()
