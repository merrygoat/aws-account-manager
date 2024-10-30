import asyncio
import datetime

from nicegui import ui

import aam.aws
from aam.models import Account, LastAccountUpdate

ui_elements = {}

@ui.page('/')
def main():

    with ui.row().classes('w-full no-wrap'):
        with ui.column().classes('w-2/3'):
            ui_elements["grid"]  = ui.aggrid({"columnDefs": [
                {'headerName': 'Name', 'field': 'name'},
                {'headerName': 'Account ID', 'field': 'id'},
                {'headerName': 'Account Status', 'field': 'status'}
            ]})
        with ui.column().classes('w-1/3'):
            ui_elements["update_button"] = ui.button("Update Account Info", on_click=update_account_info)
            ui_elements["last_updated_label"] = ui.label()

    update_last_updated_label()
    update_account_grid()

    ui.run()


def update_last_updated_label():
    last_account_update = LastAccountUpdate.get_or_none(LastAccountUpdate.id == 0)
    if last_account_update:
        ui_elements["last_updated_label"].set_text(
            f"Account information last updated: {last_account_update.time.strftime('%d/%m/%y, %H:%M:%S')}.")
    else:
        ui_elements["last_updated_label"].set_text(f"Account information last updated: None")


def update_account_grid():
    accounts = [account for account in Account.select()]
    ui_elements["grid"].options["rowData"] = [account.to_dict() for account in accounts]
    ui_elements["grid"].update()


async def update_account_info():
    with ui.dialog() as loadingDialog:
        ui.spinner(size='10em', color='black')
    loadingDialog.open()

    await asyncio.to_thread(get_and_process_account_info)

    update_last_updated_label()
    update_account_grid()

    loadingDialog.close()


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
            Account.create(id=account_details["Id"], name=account_details['Name'], status=account_details["Status"])

    LastAccountUpdate.replace(id=0, time=datetime.datetime.now()).execute()


main()
