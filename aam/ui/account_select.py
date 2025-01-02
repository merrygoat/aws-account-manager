import asyncio
import datetime
from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

import aam.aws
from aam.models import Account, LastAccountUpdate, Organization

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIAccountSelect:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        with ui.column().classes('h-full place-content-center'):
            self.organization_select = ui.select(label="Organization", options={}, on_change=self.organization_selected).classes("min-w-[400px]").props('popup-content-class="!max-h-[500px]"')
        with ui.column().classes('h-full place-content-center'):
            self.account_select = ui.select(label="Account", options={}, on_change=self.account_selected).classes("min-w-[400px]").props('popup-content-class="!max-h-[500px]"')
        with ui.grid(columns="auto auto").style("gap: 0"):
            ui.label("Show closed accounts")
            self.show_closed = ui.checkbox(on_change=self.update_account_select_options)
            ui.label("Show suspended accounts")
            self.show_suspended = ui.checkbox(on_change=self.update_account_select_options)
        with ui.column():
            self.update_button = ui.button("Update Account Info", on_click=self.update_account_info)
            self.last_updated = ui.label()

        self.update_last_updated_label()
        self.update_organization_select_options()
        self.update_account_select_options()


    def update_organization_select_options(self):
        orgs = Organization.select()
        orgs = {org.id: f"{org.name} ({org.id})" for org in orgs}
        self.organization_select.set_options(orgs)
        # Get the id of the first org in the dict
        first_org = next(iter(orgs))
        self.organization_select.set_value(first_org)

    def update_account_select_options(self):
        organization_id = self.organization_select.value

        # Uses implicit dictionary order.
        valid_status = ["ACTIVE"]
        if self.show_closed.value is True:
            valid_status.append("Closed")
        if self.show_suspended.value is True:
            valid_status.append("SUSPENDED")

        account_query = Account.select().where(Account.organization == organization_id)
        accounts = {None: "No account selected"}
        accounts.update({account.id: f"{account.name} ({account.id}) - {account.status}"
                         for account in account_query if account.status in valid_status})
        self.account_select.set_options(accounts)

    def organization_selected(self, event: nicegui.events.ValueChangeEventArguments):
        self.update_account_select_options()

    def account_selected(self, event: nicegui.events.ValueChangeEventArguments):
        selected_account_id = event.sender.value
        account = Account.get_or_none(Account.id == selected_account_id)

        self.parent.account_details.update(account)
        self.parent.set_selected_account(account)
        self.parent.bills.initialize(account)
        self.parent.notes.update_note_grid()

    async def update_account_info(self):
        with ui.dialog() as loadingDialog:
            ui.spinner(size='10em', color='black')
        loadingDialog.open()
        await asyncio.to_thread(get_and_process_account_info, self.organization_select.value)
        self.update_last_updated_label()
        self.update_account_select_options()
        loadingDialog.close()

    def update_last_updated_label(self):
        last_account_update = LastAccountUpdate.get_or_none(LastAccountUpdate.id == 0)
        if last_account_update:
            self.last_updated.set_text(
                f"Account information last updated: {last_account_update.time.strftime('%d/%m/%y, %H:%M:%S')}.")
        else:
            self.last_updated.set_text(f"Account information last updated: None")


def get_and_process_account_info(org_id: str):

    account_info = aam.aws.get_organization_accounts(org_id)
    account_info = [account for account in account_info if "SBSL" not in account["Name"]]

    if not account_info:
        ui.notify("No accounts found in organization. This is probably a permissions error.")
        return 0

    # Get organization from ARN
    organization_id = account_info[0]["Arn"].split("/")[1]
    organization = Organization.get_or_create(id=organization_id)[0]

    # Reorganize list into dict for convenient access
    account_info = {account["Id"]: account for account in account_info}

    # Loop through all accounts in DB checking against data from AWS updating as necessary.
    db_accounts = {account.id: account for account in Account.select()}
    for account_id, account in db_accounts.items():
        if account_id not in account_info:
            account.status = "Closed"
        else:
            account.status = account_info[account_id]["Status"]
        if account.organization is None:
            account.organization = organization.id
        account.save()

    # Loop through all account in AWS data, adding any that are not in the DB to the DB
    for account_id, account_details in account_info.items():
        if account_id not in db_accounts:
            Account.create(id=account_details["Id"], name=account_details["Name"], email=account_details["Email"], status=account_details["Status"], organization=organization.id)

    LastAccountUpdate.replace(id=0, time=datetime.datetime.now()).execute()
