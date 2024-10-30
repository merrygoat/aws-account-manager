from nicegui import ui

import aam.aws
from aam.models import Account


@ui.page('/')
def main():

    accounts = [account for account in Account.select()]

    with ui.row().classes('w-full no-wrap'):
        with ui.column().classes('w-2/3'):
            ui.aggrid({"columnDefs": [
                {'headerName': 'Name', 'field': 'name'},
                {'headerName': 'Account ID', 'field': 'account_id'},
                {'headerName': 'Account Status', 'field': 'account_status'}
            ],
                "rowData": [account.to_dict() for account in accounts]
            })
        with ui.column().classes('w-1/3'):
            ui.button("Update Account Info", on_click=)
    ui.run()


def update_account_info():
    account_info = aam.aws.get_accounts("management-hrds")

main()
