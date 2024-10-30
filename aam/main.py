import datetime

from nicegui import ui

import aam.aws
from aam.models import Account, LastAccountUpdate

ui_elements = {}

@ui.page('/')
def main():

    accounts = [account for account in Account.select()]

    with ui.row().classes('w-full no-wrap'):
        with ui.column().classes('w-2/3'):
            ui_elements["grid"]  = ui.aggrid({"columnDefs": [
                {'headerName': 'Name', 'field': 'name'},
                {'headerName': 'Account ID', 'field': 'id'},
                {'headerName': 'Account Status', 'field': 'status'}
            ],
                "rowData": [account.to_dict() for account in accounts]
            })
        with ui.column().classes('w-1/3'):
            ui_elements["update_button"] = ui.button("Update Account Info", on_click=update_account_info)
            last_account_update = LastAccountUpdate.get_or_none(LastAccountUpdate.id == 0)
            if last_account_update:
                time = last_account_update.time
            else:
                time = "None"
            ui_elements["last_updated_label"] = ui.label(f"Account information last updated: {time.strftime('%d/%m/%y, %H:%M:%S')}.")
    ui.run()


async def update_account_info():
    # with ui.dialog() as loadingDialog:
    #     ui.spinner(size='10em', color='black')
    # loadingDialog.open()

    account_info = aam.aws.get_accounts("hrds-management")
    account_info = [account for account in account_info if "SBSL" not in account["Name"]]
    account_info = {account["Id"]: account for account in account_info}

    db_accounts = [account for account in Account.select()]
    for account in db_accounts:
        if account.account_id not in account_info:
            account.status = "Closed"
        else:
            account.status = account_info[account.account_id]["Status"]
        account.save()

    for account_id, account_details in account_info.items():
        if account_id not in db_accounts:
            Account.create(id=account_details["Id"], name=account_details['Name'], status=account_details["Status"])

    LastAccountUpdate.replace(id=0, time=datetime.datetime.now()).execute()

    # loadingDialog.close()

main()
