import asyncio
import datetime
from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

import aam.aws
from aam.models import Account, LastAccountUpdate

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIAccountSelect:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        accounts = {account.id: f"{account.name} ({account.id}) - {account.status}" for account in Account.select()}

        with ui.row():
            self.account_select = ui.select(label="Account", options=accounts, on_change=self.account_selected).classes("min-w-[400px]").props('popup-content-class="!max-h-[500px]"')
            self.update_button = ui.button("Update Account Info", on_click=self.update_account_info)
            self.last_updated = ui.label()


        self.update_last_updated_label()


    def account_selected(self, event: nicegui.events.ValueChangeEventArguments):
        selected_account_id = event.sender.value
        account = Account.get_or_none(Account.id == selected_account_id)

        self.parent.account_details.update(account)
        self.parent.bills.initialize(account)
        self.parent.notes.update_note_grid(account)


    async def update_account_info(self):
        with ui.dialog() as loadingDialog:
            ui.spinner(size='10em', color='black')
        loadingDialog.open()

        await asyncio.to_thread(get_and_process_account_info)

        self.update_last_updated_label()

        loadingDialog.close()

    def update_last_updated_label(self):
        last_account_update = LastAccountUpdate.get_or_none(LastAccountUpdate.id == 0)
        if last_account_update:
            self.last_updated.set_text(
                f"Account information last updated: {last_account_update.time.strftime('%d/%m/%y, %H:%M:%S')}.")
        else:
            self.last_updated.set_text(f"Account information last updated: None")


def get_and_process_account_info():

    account_info = aam.aws.get_accounts("hrds-management")
    account_info = [account for account in account_info if "SBSL" not in account["Name"]]
    account_info = {account["Id"]: account for account in account_info}

    # Loop through all accounts in DB checking against data from AWS updating as necessary.
    db_accounts = {account.id: account for account in Account.select()}
    for account_id, account in db_accounts.items():
        if account_id not in account_info:
            account.status = "Closed"
        else:
            account.status = account_info[account_id]["Status"]
        account.save()

    # Loop through all account in AWS data, adding any that are not in the DB to the DB
    for account_id, account_details in account_info.items():
        if account_id not in db_accounts:
            Account.create(id=account_details["Id"], name=account_details["Name"], email=account_details["Email"], status=account_details["Status"])

    LastAccountUpdate.replace(id=0, time=datetime.datetime.now()).execute()
