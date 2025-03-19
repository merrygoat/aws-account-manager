import asyncio
import datetime
from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui
from peewee import JOIN

import aam.aws
from aam.models import Account, LastAccountUpdate, Organization, Person

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

        self.update_last_updated_label(self.organization_select.value)
        self.update_organization_select_options()
        self.update_account_select_options()

    def update_organization_select_options(self):
        orgs = Organization.select()
        orgs = {org.id: f"{org.name} ({org.id})" for org in orgs}
        self.organization_select.set_options(orgs)

    def update_account_select_options(self):
        organization_id = self.organization_select.value

        # Uses implicit dictionary order.
        valid_status = ["ACTIVE"]
        if self.show_closed.value is True:
            valid_status.append("Closed")
        if self.show_suspended.value is True:
            valid_status.append("SUSPENDED")

        accounts = sorted(list(Account.select().where(Account.organization == organization_id)),
                          key=lambda item: item.name)

        account_items = {None: "No account selected"}
        account_items.update({account.id: f"{account.name} ({account.id}) - {account.status}"
                              for account in accounts if account.status in valid_status})
        self.account_select.set_options(account_items)

    def organization_selected(self, event: nicegui.events.ValueChangeEventArguments):
        selected_org_id = event.sender.value
        current_org_id = self.parent.get_selected_organization_id()
        # Need to add this test as the callback fires multiple times per select.
        if selected_org_id != current_org_id:
            self.update_account_select_options()
            self.parent.set_selected_organization_id(selected_org_id)

    def account_selected(self, event: nicegui.events.ValueChangeEventArguments):
        selected_account_id = event.sender.value
        current_account_id = self.parent.get_selected_account_id()
        if selected_account_id != current_account_id:
            account = (Account.select(Account, Person)
                       .where(Account.id == selected_account_id)
                       .join_from(Account, Person, JOIN.LEFT_OUTER)).get_or_none()

            self.parent.account_details.update(account)
            self.parent.set_selected_account_id(account)
            self.parent.transactions.initialize(account)
            self.parent.account_details.notes.update_note_grid()

    async def update_account_info(self):
        selected_organization = self.organization_select.value
        if not selected_organization:
            ui.notify("No organization selected.")
            return 0

        with ui.dialog() as loadingDialog:
            ui.spinner(size='10em', color='black')
        loadingDialog.open()
        await asyncio.to_thread(get_and_process_account_info, self.organization_select.value)
        self.update_last_updated_label(self.organization_select.value)
        self.update_account_select_options()
        loadingDialog.close()

    def update_last_updated_label(self, organization_id: str | None):
        if not organization_id:
            text = "None"
        else:
            last_account_update = LastAccountUpdate.get_or_create(organization=organization_id)[0]
            if last_account_update.time:
                text = last_account_update.time.strftime('%d/%m/%y, %H:%M:%S')
            else:
                text = "None"
        self.last_updated.set_text(f"Account information last updated: {text}")

    def select_default_org(self):
        # Get the id of the first org in the dict
        if self.organization_select.options:
            first_org = next(iter(self.organization_select.options))
            self.organization_select.set_value(first_org)


def get_and_process_account_info(org_id: str):

    organization = Organization.get_or_create(id=org_id)[0]

    account_info = aam.aws.get_organization_accounts(org_id)
    account_info = {account["Id"]: account for account in account_info if "SBSL" not in account["Name"]}

    if not account_info:
        ui.notify("No accounts found in organization. This is probably a permissions error.")
        return 0

    # Loop through all accounts in DB checking against data from AWS updating as necessary.
    db_accounts = {account.id: account for account in Account.select().where(Account.organization==org_id)}
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

    last_updated = LastAccountUpdate.get_or_create(organization=org_id)[0]
    last_updated.time=datetime.datetime.now()
    last_updated.save()
