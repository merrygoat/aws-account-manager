import datetime
import decimal
import re
from typing import TYPE_CHECKING, Iterable

import nicegui.events
from nicegui import ui
from peewee import JOIN, fn

import aam.utilities
from aam.models import SharedCharge, Account, Month, AccountJoinSharedCharge, MonthlyUsage

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
        """Delete the selected SharedCharge and recalculate the SharedCharge amounts """
        selected_row = await self.shared_charges_table.get_selected_row()
        if selected_row is None:
            ui.notify("No shared charge selected.")
        else:
            shared_charge: SharedCharge = SharedCharge.get(SharedCharge.id==selected_row["id"])
            date = shared_charge.date
            shared_charge.delete_instance()
            calculate_shared_charge_per_account(date)
            self.populate_shared_charges_table()
            ui.notify("Shared charge deleted.")

    def populate_shared_charges_table(self):
        charge_details = []
        selected_organization = self.parent.get_selected_organization_id()
        if selected_organization:
            shared_charges: Iterable[SharedCharge] = (
                SharedCharge.select(SharedCharge, AccountJoinSharedCharge, Account.name)
                .join(AccountJoinSharedCharge)
                .join(Account)
                .where(Account.organization == self.parent.get_selected_organization_id()))

            # One record is returned for each account in each shared charge
            # Sort shared charges into dict using charge id as the index
            sorted_shared_charges = {}
            for charge in shared_charges:
                sorted_shared_charges.setdefault(charge.id, []).append(charge)

            for charge_id, charges in sorted_shared_charges.items():
                date = charges[0].date
                account_names = [charge.accountjoinsharedcharge.account.name for charge in charges]
                account_names = ", ".join(sorted(account_names))
                charge_details.append({"id": charge_id, "name": charges[0].name, "amount": charges[0].amount,
                                       "month": date, "account_names": account_names})

        self.shared_charges_table.options["rowData"] = charge_details
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
                    self.month = aam.utilities.month_select()
                    ui.label("Year")
                    self.year = aam.utilities.year_select()
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
        """Populate the account select element with a list of ACTIVE accounts in the currently selected organization"""
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
        """Take the information from the dialog and use it to either update an existing SharedCharge if editing or
        create a new SharedCharge if creating a new one."""
        if not self.validate_inputs():
            return 0

        date = datetime.date(self.year.value, self.month.value, 1)
        amount = decimal.Decimal(self.amount.value)

        affected_accounts: list[str] = []

        if not self.shared_charge_id:
            shared_charge = SharedCharge.create(name=self.name.value, amount=amount, date=date)
            affected_accounts.extend(self.account_select.value)
        else:

            # Get existing SharedCharge
            shared_charge: SharedCharge = SharedCharge.get(SharedCharge.id == self.shared_charge_id)
            shared_charge.name = self.name.value
            shared_charge.amount = amount
            shared_charge.date = date
            shared_charge.save()

            # Delete AccountJoinSharedCharges currently associated with the Shared Charge
            AccountJoinSharedCharge.delete().where(AccountJoinSharedCharge.shared_charge == shared_charge.id).execute()

        for account_id in self.account_select.value:
            AccountJoinSharedCharge.create(account=account_id, shared_charge=shared_charge.id)

        calculate_shared_charge_per_account(date)

        self.parent.populate_shared_charges_table()
        self.parent.parent.transactions.update_transaction_grid()
        if self.shared_charge_id:
            ui.notify("Shared charge edited.")
        else:
            ui.notify("New shared charge added.")
        self.close()


    def validate_inputs(self) -> bool:
        """Validate the fields in the dialog. Returns True if all inputs are valid, else returns False."""
        if self.name == "":
            ui.notify("Name must be provided.")
            return False
        try:
            decimal.Decimal(self.amount.value)
        except decimal.InvalidOperation:
            ui.notify("Amount is not a valid number.")
            return False
        return True

    def open(self, shared_charge: SharedCharge | None = None, mode: str = "new"):
        # Possible modes are "new", "edit" or "duplicate"

        self.update_account_select()

        if mode == "edit":
            self.shared_charge_id = shared_charge.id

        if mode != "new":
            # Get accounts associated with exising shared charge
            accounts = (Account.select(Account.id).where(SharedCharge.id == shared_charge.id)
                        .join(AccountJoinSharedCharge)
                        .join(SharedCharge).dicts())
            account_ids = [account["id"] for account in accounts]

            self.name.set_value(shared_charge.name)
            self.month.set_value(shared_charge.date.month)
            self.year.set_value(shared_charge.date.year)
            self.amount.set_value(str(shared_charge.amount))
            self.account_select.set_value(account_ids)

        self.dialog.open()

    def close(self):
        self.shared_charge_id = None
        self.dialog.close()


def calculate_shared_charge_per_account(date: datetime.date):
    """Calculate the total of all SharedCharges assigned to an Account in the month given by `date` and assign this
    value to the Account.shared_charge field."""

    # Get the accounts and the ids of shared charges in the current month
    accounts: list[dict] = (
        SharedCharge.select(SharedCharge.id, AccountJoinSharedCharge.account_id)
        .join(AccountJoinSharedCharge, JOIN.LEFT_OUTER)
        .where(SharedCharge.date == date).dicts()
    )
    # Group by account
    grouped_accounts = {}
    for account in accounts:
        grouped_accounts.setdefault(account["account"], []).append(account["id"])
    amount_per_account = (
        SharedCharge.select(
            (SharedCharge.amount / fn.COUNT(AccountJoinSharedCharge.shared_charge_id)).alias("amount_per_account"),
            SharedCharge.id)
        .join(AccountJoinSharedCharge, JOIN.LEFT_OUTER)
        .where(SharedCharge.date == date)
        .group_by(SharedCharge.id)
        .dicts()
    )
    # Group by SharedCharge id
    amount_per_account = {row["id"]: row["amount_per_account"] for row in amount_per_account}
    month_code = aam.utilities.month_code(date.year, date.month)
    for account_id in grouped_accounts:
        total = 0
        for shared_charge_id in grouped_accounts[account_id]:
            total += amount_per_account[shared_charge_id]
        monthly_usage: MonthlyUsage = MonthlyUsage.get((MonthlyUsage.account_id == account_id) & (MonthlyUsage.month_id == month_code))
        monthly_usage.shared_charge = total
        monthly_usage.save()
