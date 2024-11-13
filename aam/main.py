import asyncio
import datetime
from functools import partial

import nicegui.events
from nicegui import ui

import aam.aws
from aam import note_dialog
from aam.models import Account, LastAccountUpdate, Person, Sysadmin, Note

ui_elements = {}

@ui.page('/')
def main():

    people = [person for person in Person.select()]
    if not people:
        Person.create(first_name="Peter", last_name="Crowther", email="peter@internet.com")
        Person.create(first_name="Felix", last_name="Edelsten", email="felix@internet.com")
        Person.create(first_name="Connor", last_name="Main", email="connor@internet.com")

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

    with ui.row().classes('w-full no-wrap'):
        with ui.column().classes('w-1/2'):
            ui.html("Account Details").classes("text-2xl")
            with ui.grid(columns='auto 1fr').classes('w-full'):
                ui.label("Name:")
                ui_elements["account_name"] = ui.label("")
                ui.label("Account ID:")
                ui_elements["account_id"] = ui.label("")
                ui.label("Root Email:")
                ui_elements["root_email"] = ui.label("")
                ui.label("Account Status:")
                ui_elements["account_status"] = ui.label("")
                ui.html("Billing/Contact Details").classes("text-2xl")
                ui.element()
                ui.label("Budget Holder:")
                ui_elements["budget_holder"] = ui.select([], on_change=partial(update_email, "budget_holder")).props("clearable outlined")
                ui.label("Budget Holder email:")
                ui_elements["budget_holder_email"] = ui.label("")
                ui.label("Finance Code:")
                ui_elements["finance_code"] = ui.input().props("clearable outlined")
                ui.label("Task Code:")
                ui_elements["task_code"] = ui.input().props("clearable outlined ")
                ui.label("Sysadmin:")
                ui_elements["sysadmin"] = ui.select([], on_change=partial(update_email, "sysadmin")).props("clearable outlined")
                ui.label("Sysadmin email:")
                ui_elements["sysadmin_email"] = ui.label("")
        with ui.column().classes('w-1/2'):
            ui.html("Notes").classes("text-xl")
            ui_elements["notes_grid"] = ui.aggrid({
                'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                               {"headerName": "Date", "field": "date"},
                               {"headerName": "Note", "field": "text"}],
                'rowData': {},
                'rowSelection': 'multiple',
                'stopEditingWhenCellsLoseFocus': True,
            })
            note_dialog.add_note_dialog(ui_elements)
            note_dialog.edit_note_dialog(ui_elements)
            with ui.row():
                ui.button('Add note', on_click=lambda: ui_elements["note_dialog"].open())
                ui.button('Edit note', on_click=partial(note_dialog.open_edit_note_dialog, ui_elements))


    ui_elements["save_changes"] = ui.button("Save Changes", on_click=save_changes)
    ui.button("Freeze", on_click=freeze)

    ui_elements["grid"].on("RowSelected", account_selected)
    ui_elements["notes_grid"].on("RowDoubleClick", lambda event: ui.notify(event))


    ui_elements["budget_holder"].disable()
    ui_elements["sysadmin"].disable()
    ui_elements["finance_code"].disable()
    ui_elements["task_code"].disable()
    ui_elements["save_changes"].disable()
    update_last_updated_label()
    update_account_grid()

    ui.run()


def freeze():
    pass

def update_email(email_type: str, event: nicegui.events.ValueChangeEventArguments):
    selected_sysadmin = event.sender.value
    if selected_sysadmin:
        person = Person.get(id=selected_sysadmin)
        ui_elements[f"{email_type}_email"].set_text(person.email)
    else:
        ui_elements[f"{email_type}_email"].set_text("")

def account_selected(event: nicegui.events.GenericEventArguments):
    row_data = event.args['data']
    if event.args["selected"] is True:
        ui_elements["sysadmin"].enable()
        ui_elements["budget_holder"].enable()
        ui_elements["save_changes"].enable()
        ui_elements["finance_code"].enable()
        ui_elements["task_code"].enable()

        ui_elements["account_name"].set_text(row_data["name"])
        ui_elements["account_id"].set_text(row_data["id"])
        ui_elements["root_email"].set_text(row_data["email"])
        ui_elements["account_status"].set_text(row_data["status"])
        all_people = {person.id: person.full_name for person in Person.select()}
        account = Account.get_or_none(Account.id == row_data["id"])

        ui_elements["budget_holder"].set_options(all_people)
        ui_elements["finance_code"].set_value(account.finance_code)
        ui_elements["task_code"].set_value(account.task_code)
        ui_elements["sysadmin"].set_options(all_people)
        if account:
            if account.budget_holder:
                ui_elements["budget_holder"].set_value(account.budget_holder.id)
            else:
                ui_elements["budget_holder"].set_value(None)

            sysadmin = account.sysadmin.get_or_none()
            if sysadmin:
                ui_elements["sysadmin"].set_value(sysadmin.person.id)
            else:
                ui_elements["sysadmin"].set_value(None)
        else:
            ui_elements["sysadmin"].set_value(None)
            ui_elements["sysadmin"].set_value(None)
        notes = [note for note in Note.select().where(Note.account_id == account.id)]
        if notes:
            notes = [{"id": note.id, "date": note.date, "text": note.text} for note in notes]
        else:
            notes = []
        ui_elements["notes_grid"].options["rowData"] = notes
        ui_elements["notes_grid"].update()

    elif event.args["selected"] is False and row_data['id'] == ui_elements["account_id"].text:
        ui_elements["account_name"].set_text("")
        ui_elements["account_id"].set_text("")
        ui_elements["root_email"].set_text("")
        ui_elements["account_status"].set_text("")
        ui_elements["budget_holder"].set_value(None)
        ui_elements["budget_holder_email"].set_text("")
        ui_elements["finance_code"].set_value(None)
        ui_elements["task_code"].set_value(None)
        ui_elements["sysadmin"].set_value(None)
        ui_elements["sysadmin_email"].set_text("")
        ui_elements["finance_code"].disable()
        ui_elements["task_code"].disable()
        ui_elements["budget_holder"].disable()
        ui_elements["sysadmin"].disable()
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
    selected_sysadmin = ui_elements["sysadmin"].value
    if selected_sysadmin:
        selected_sysadmin = Person.get(Person.id == selected_sysadmin)
        Sysadmin.create(person=selected_sysadmin, account=account)
    else:
        account.sysadmin.get().delete_instance()
    selected_budgetholder = ui_elements["budget_holder"].value
    if selected_budgetholder:
        selected_budgetholder = Person.get(Person.id == selected_budgetholder)
        account.budget_holder = selected_budgetholder
    else:
        account.budget_holder = None
    ui.notify("Record updated.")
    account.finance_code = ui_elements["finance_code"].value
    account.task_code = ui_elements["task_code"].value
    account.save()

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
