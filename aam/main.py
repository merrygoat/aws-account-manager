import asyncio
import datetime

import nicegui.events
from nicegui import ui

import aam.aws
from aam.models import Account, LastAccountUpdate, Person, BudgetHolder

ui_elements = {}

@ui.page('/')
def main():

    people = [person for person in Account.select()]
    if not people:
        Person.create(first_name="Peter", last_name="Crowther", email="peter@internet.com")

    grid_options = {
        'defaultColDef': {},
        'columnDefs': [
            {'headerName': 'Name', 'field': 'name', 'checkboxSelection': True},
            {'headerName': 'Account ID', 'field': 'id'},
            {'headerName': 'Root Email', 'field': 'email'},
            {'headerName': 'Account Status', 'field': 'status'}
        ]}

    with ui.row().classes('w-full no-wrap'):
        with ui.column().classes('w-2/3'):
            ui_elements["grid"]  = ui.aggrid(grid_options)
        with ui.column().classes('w-1/3'):
            ui_elements["update_button"] = ui.button("Update Account Info", on_click=update_account_info)
            ui_elements["last_updated_label"] = ui.label()
    ui.separator()
    with ui.grid(columns='100px 200px').classes('w-full'):
        ui.label("Name:").classes('place-content-center')
        ui_elements["account_name"] = ui.label("")
        ui.label("Account ID:").classes('place-content-center')
        ui_elements["account_id"] = ui.label("")
        ui.label("Root Email:").classes('place-content-center')
        ui_elements["root_email"] = ui.label("")
        ui.label("Account Status:").classes('place-content-center')
        ui_elements["account_status"] = ui.label("")
        ui.label("Budget Holder:").classes('place-content-center')
        ui_elements["budget_holder"] = ui.select([]).props("clearable")
    ui_elements["save_changes"] = ui.button("Save Changes", on_click=save_changes)
    ui.button("Freeze", on_click=freeze)

    ui_elements["grid"].on("RowSelected", update_details_window)

    ui_elements["budget_holder"].disable()
    ui_elements["save_changes"].disable()
    update_last_updated_label()
    update_account_grid()

    ui.run()

def freeze():
    pass

def update_details_window(event: nicegui.events.GenericEventArguments):
    row_data = event.args['data']
    if event.args["selected"] is True:
        ui_elements["account_name"].set_text(row_data["name"])
        ui_elements["account_id"].set_text(row_data["id"])
        ui_elements["root_email"].set_text(row_data["email"])
        ui_elements["account_status"].set_text(row_data["status"])
        all_people = {person.id: person.full_name for person in Person.select()}
        ui_elements["budget_holder"].set_options(all_people)
        account = Account.get_or_none(Account.id == row_data["id"])
        if account:
            budget_holder = account.budget_holder.get_or_none()
            if budget_holder:
                ui_elements["budget_holder"].set_value(budget_holder.person.id)
            else:
                ui_elements["budget_holder"].set_value(None)
        else:
            ui_elements["budget_holder"].set_value(None)
        ui_elements["budget_holder"].enable()
        ui_elements["save_changes"].enable()
    elif event.args["selected"] is False and row_data['id'] == ui_elements["account_id"].text:
        ui_elements["account_name"].set_text("")
        ui_elements["account_id"].set_text("")
        ui_elements["root_email"].set_text("")
        ui_elements["account_status"].set_text("")
        ui_elements["budget_holder"].set_value(None)
        ui_elements["budget_holder"].disable()
        ui_elements["save_changes"].disable()

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


def save_changes():
    account = Account.get(Account.id==ui_elements["account_id"].text)
    new_budget_holder = ui_elements["budget_holder"].value
    if new_budget_holder:
        new_budget_holder = Person.get(Person.id == new_budget_holder)
        BudgetHolder.create(person=new_budget_holder, account=account)
    else:
        account.budget_holder.get().delete_instance()
    ui.notify("Record updated.")

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
            Account.create(id=account_details["Id"], name=account_details["Name"], email=account_details["Email"], status=account_details["Status"])

    LastAccountUpdate.replace(id=0, time=datetime.datetime.now()).execute()


main()
