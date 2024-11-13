import asyncio
import datetime

import nicegui.events
from nicegui import ui

import aam.aws
from aam import note_dialog
from aam.models import Account, LastAccountUpdate, Person, Sysadmin, Note


@ui.page('/')
def main():

    people = [person for person in Person.select()]
    if not people:
        Person.create(first_name="Peter", last_name="Crowther", email="peter@internet.com")
        Person.create(first_name="Felix", last_name="Edelsten", email="felix@internet.com")
        Person.create(first_name="Connor", last_name="Main", email="connor@internet.com")

    main_form = MainForm()

    ui.run()


class MainForm:
    def __init__(self):
        with ui.row().classes('w-full no-wrap'):
            self.account_grid = AccountList(self)
        ui.separator()

        with ui.row().classes('w-full no-wrap'):
            with ui.column().classes('w-1/2'):
                self.account_details = AccountDetails(self)
            with ui.column().classes('w-1/2'):
                self.notes = AccountNotes(self)

        self.save_changes = ui.button("Save Changes", on_click=self.save_account_changes)
        self.freeze = ui.button("Freeze", on_click=freeze)

        self.save_changes.disable()

    def save_account_changes(self):
        account = Account.get(Account.id == self.account_details.account_id.text)
        selected_sysadmin = self.account_details.sysadmin.value
        if selected_sysadmin:
            selected_sysadmin = Person.get(Person.id == selected_sysadmin)
            Sysadmin.create(person=selected_sysadmin, account=account)
        else:
            account.sysadmin.get().delete_instance()
        selected_budgetholder = self.account_details.budget_holder.value
        if selected_budgetholder:
            selected_budgetholder = Person.get(Person.id == selected_budgetholder)
            account.budget_holder = selected_budgetholder
        else:
            account.budget_holder = None
        ui.notify("Record updated.")
        account.finance_code = self.account_details.finance_code.value
        account.task_code = self.account_details.task_code.value
        account.save()


class AccountDetails:
    def __init__(self, parent: MainForm):
        self.parent = parent

        ui.html("Account Details").classes("text-2xl")
        with ui.grid(columns='auto 1fr').classes('w-full'):
            ui.label("Name:")
            self.account_name = ui.label("")
            ui.label("Account ID:")
            self.account_id = ui.label("")
            ui.label("Root Email:")
            self.root_email = ui.label("")
            ui.label("Account Status:")
            self.account_status = ui.label("")
            ui.html("Billing/Contact Details").classes("text-2xl")
            ui.element()
            ui.label("Budget Holder:")
            self.budget_holder = ui.select([], on_change=self.update_budget_holder_email).props(
                "clearable outlined")
            ui.label("Budget Holder email:")
            self.budget_holder_email = ui.label("")
            ui.label("Finance Code:")
            self.finance_code = ui.input().props("clearable outlined")
            ui.label("Task Code:")
            self.task_code = ui.input().props("clearable outlined ")
            ui.label("Sysadmin:")
            self.sysadmin = ui.select([], on_change=self.update_sysadmin_email).props(
                "clearable outlined")
            ui.label("Sysadmin email:")
            self.sysadmin_email = ui.label("")

        self.budget_holder.disable()
        self.sysadmin.disable()
        self.finance_code.disable()
        self.task_code.disable()

    def update_sysadmin_email(self, event: nicegui.events.ValueChangeEventArguments):
        selected_person = event.sender.value
        if selected_person:
            person = Person.get(id=selected_person)
            self.sysadmin_email.set_text(person.email)
        else:
            self.sysadmin_email.set_text("")

    def update_budget_holder_email(self, event: nicegui.events.ValueChangeEventArguments):
        selected_person = event.sender.value
        if selected_person:
            person = Person.get(id=selected_person)
            self.budget_holder_email.set_text(person.email)
        else:
            self.budget_holder_email.set_text("")

    def clear(self):
        self.account_name.set_text("")
        self.account_id.set_text("")
        self.root_email.set_text("")
        self.account_status.set_text("")
        self.budget_holder.set_value(None)
        self.budget_holder_email.set_text("")
        self.finance_code.set_value(None)
        self.task_code.set_value(None)
        self.sysadmin.set_value(None)
        self.sysadmin_email.set_text("")
        self.finance_code.disable()
        self.task_code.disable()
        self.budget_holder.disable()
        self.sysadmin.disable()

    def update(self, account_info: dict):
        self.sysadmin.enable()
        self.budget_holder.enable()
        self.finance_code.enable()
        self.task_code.enable()

        self.account_name.set_text(account_info["account_name"])
        self.account_id.set_text(account_info["id"])
        self.root_email.set_text(account_info["email"])
        self.account_status.set_text(account_info["status"])

        all_people = {person.id: person.full_name for person in Person.select()}
        self.budget_holder.set_options(all_people)
        self.sysadmin.set_options(all_people)

        selected_account = account_info["account"]
        self.finance_code.set_value(selected_account.finance_code)
        self.task_code.set_value(selected_account.task_code)
        if selected_account:
            if selected_account.budget_holder:
                self.budget_holder.set_value(selected_account.budget_holder.id)
            else:
                self.budget_holder.set_value(None)

            sysadmin = selected_account.sysadmin.get_or_none()
            if sysadmin:
                self.sysadmin.set_value(sysadmin.person.id)
            else:
                self.sysadmin.set_value(None)
        else:
            self.sysadmin.set_value(None)


class AccountNotes:
    def __init__(self, parent: MainForm):
        self.parent = parent
        ui.html("Notes").classes("text-xl")
        self.notes_grid = ui.aggrid({
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Date", "field": "date"},
                           {"headerName": "Note", "field": "text"}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })
        self.add_note_dialog = note_dialog.AddNoteDialog(self)
        self.edit_note_dialog = note_dialog.EditNoteDialog(self)
        with ui.row():
            ui.button('Add note', on_click=self.add_note_dialog.open)
            ui.button('Edit note', on_click=self.edit_note_dialog.open)

    def update_note_grid(self, account: Account):
        notes = [note for note in Note.select().where(Note.account_id == account.id)]
        if notes:
            notes = [{"id": note.id, "date": note.date, "text": note.text} for note in notes]
        else:
            notes = []
        self.notes_grid.options["rowData"] = notes
        self.notes_grid.update()


class AccountList:
    def __init__(self, parent: MainForm):
        self.parent = parent

        grid_options = {
            'defaultColDef': {},
            'columnDefs': [
                {'headerName': 'Name', 'field': 'name', 'checkboxSelection': True},
                {'headerName': 'Account ID', 'field': 'id'},
                {'headerName': 'Root Email', 'field': 'email'},
                {'headerName': 'Account Status', 'field': 'status'}
            ]}

        with ui.column().classes('w-2/3'):
            self.grid = ui.aggrid(grid_options)
        with ui.column().classes('w-1/3'):
            self.update_button = ui.button("Update Account Info", on_click=self.update_account_info)
            self.last_updated = ui.label()

        self.grid.on("RowSelected", self.account_selected)
        self.update_last_updated_label()
        self.update_account_grid()

    def account_selected(self, event: nicegui.events.GenericEventArguments):
        row_data = event.args['data']
        if event.args["selected"] is True:
            self.parent.save_changes.enable()

            account = Account.get_or_none(Account.id == row_data["id"])

            account_info = {"account_name": row_data["name"],
                            "id": row_data["id"],
                            "email": row_data["email"],
                            "status": row_data["status"],
                            "account": account}

            self.parent.account_details.update(account_info)

            self.parent.notes.update_note_grid(account)

        elif event.args["selected"] is False and row_data['id'] == self.parent.account_details.account_id.text:
            self.parent.account_details.clear()
            self.parent.save_changes.disable()

    async def update_account_info(self):
        with ui.dialog() as loadingDialog:
            ui.spinner(size='10em', color='black')
        loadingDialog.open()

        await asyncio.to_thread(get_and_process_account_info)

        self.update_last_updated_label()
        self.update_account_grid()

        loadingDialog.close()

    def update_last_updated_label(self):
        last_account_update = LastAccountUpdate.get_or_none(LastAccountUpdate.id == 0)
        if last_account_update:
            self.last_updated.set_text(
                f"Account information last updated: {last_account_update.time.strftime('%d/%m/%y, %H:%M:%S')}.")
        else:
            self.last_updated.set_text(f"Account information last updated: None")

    def update_account_grid(self):
        accounts = [account for account in Account.select()]
        self.grid.options["rowData"] = [account.to_dict() for account in accounts]
        self.grid.update()

def freeze():
    pass


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
