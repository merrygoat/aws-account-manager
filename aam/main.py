import asyncio
import datetime
from typing import Optional

import nicegui.events
from nicegui import ui

import aam.aws
from aam import note_dialog, initialization
from aam.models import Account, LastAccountUpdate, Person, Sysadmin, Note, Month, Bill
from aam.utilities import get_bill_months


@ui.page('/')
def main():

    initialization.initialize()

    main_form = UIMainForm()

    ui.run()


class UIMainForm:
    def __init__(self):
        with ui.row().classes('w-full no-wrap'):
            self.account_grid = UIAccountSelect(self)
        ui.separator()

        with ui.row().classes('w-full no-wrap'):
            with ui.column().classes('w-1/3'):
                self.account_details = UIAccountDetails(self)
                self.notes = UIAccountNotes(self)
            with ui.column().classes('w-2/3'):
                self.bills = UIBills(self)
                self.exchange_rate = UIExchangeRate(self)

class UIExchangeRate:
    def __init__(self, parent: UIMainForm):
        self.parent = parent

        self.month_grid = ui.aggrid({
            "defaultColDef": {"sortable": False},
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Month", "field": "month", "cellDataType": "string"},
                           {"headerName": "Exchange rate £/$", "field": "exchange_rate", "editable": True}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })
        months = [{"id": month.id, "month": month.date.strftime("%b-%y"), "exchange_rate": month.exchange_rate} for month in Month.select()]
        self.month_grid.on("cellValueChanged", self.update_exchange_rate)
        self.month_grid.options["rowData"] = months
        self.month_grid.update()

    @staticmethod
    def update_exchange_rate(event: nicegui.events.GenericEventArguments):
        month_id = event.args["data"]["id"]
        month = Month.get(id=month_id)
        month.exchange_rate = event.args["data"]["exchange_rate"]
        month.save()


class UIBills:
    def __init__(self, parent):
        self.parent = parent
        self.selected_account: Optional[Account] = None
        ui.html("Money").classes("text-2xl")
        self.bill_grid = ui.aggrid({
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Month", "field": "month", "sort": "desc"},
                           {"headerName": "Usage ($)", "field": "usage_dollar", "editable": True},
                           {"headerName": "Usage (£)", "field": "usage_pound",
                            "valueFormatter": "value.toFixed(2)"}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })
        self.bill_grid.on("cellValueChanged", self.update_bill)

    def initialize(self, account: Account):
        """This function is run when an account is selected from the dropdown menu."""
        self.selected_account = account
        if account.creation_date:
            bills = account.get_bills()
            required_bill_months = get_bill_months(account.creation_date, account.final_date())
            actual_bill_months = [bill["month"] for bill in bills]
            missing_months = set(required_bill_months) - set(actual_bill_months)

            if missing_months:
                for month in missing_months:
                    Bill.get_or_create(account_id=account.id, month_id=Month.get(date=month))
                bills = account.get_bills()
            self.bill_grid.options["rowData"] = bills
        else:
            self.bill_grid.options["rowData"] = {}
        self.bill_grid.update()

    def update_grid(self):
        bills = self.selected_account.get_bills()
        self.bill_grid.options["rowData"] = bills
        self.bill_grid.update()
        
    def update_bill(self, event: nicegui.events.GenericEventArguments):
        bill_id = event.args["data"]["id"]
        bill = Bill.get(id=bill_id)
        bill.usage = event.args["data"]["usage_dollar"]
        bill.save()
        self.update_grid()

class UIAccountDetails:
    def __init__(self, parent: UIMainForm):
        self.parent = parent

        ui.html("Account Details").classes("text-2xl")
        with ui.grid(columns='auto 1fr').classes('w-full'):
            ui.label("Name:")
            self.account_name = ui.label("").classes("place-content-center")
            ui.label("Account ID:")
            self.account_id = ui.label("").classes("place-content-center")
            ui.label("Root Email:")
            self.root_email = ui.label("").classes("place-content-center")
            ui.label("Account Status:")
            self.account_status = ui.label("")
            ui.html("Billing/Contact Details").classes("text-2xl")
            ui.element()
            ui.label("Budget Holder:").classes("place-content-center")
            self.budget_holder = ui.select([], on_change=self.update_budget_holder_email).props(
                "clearable outlined dense")
            ui.label("Budget Holder email:").classes("place-content-center")
            self.budget_holder_email = ui.label("")
            ui.label("Finance Code:").classes("place-content-center")
            self.finance_code = ui.input().props("clearable outlined dense")
            ui.label("Task Code:").classes("place-content-center")
            self.task_code = ui.input().props("clearable outlined dense")
            ui.label("Sysadmin:").classes("place-content-center")
            self.sysadmin = ui.select([], on_change=self.update_sysadmin_email).props(
                "clearable outlined dense")
            ui.label("Sysadmin email:")
            self.sysadmin_email = ui.label("")
            ui.label("Creation date").classes("place-content-center")
            with ui.input('Date').props("dense") as self.account_creation_input:
                with ui.menu().props('no-parent-event') as account_creation_menu:
                    with ui.date().bind_value(self.account_creation_input) as self.account_creation_date:
                        with ui.row().classes('justify-end'):
                            ui.button('Close', on_click=account_creation_menu.close).props('flat')
                with self.account_creation_input.add_slot('append'):
                    ui.icon('edit_calendar').on('click', account_creation_menu.open).classes('cursor-pointer')
            ui.label("Closure date").classes("place-content-center")
            with ui.input('Date').props("dense") as self.account_closure_input:
                with ui.menu().props('no-parent-event') as account_closure_menu:
                    with ui.date().bind_value(self.account_closure_input) as self.account_closure_date:
                        with ui.row().classes('justify-end'):
                            ui.button('Close', on_click=account_closure_menu.close).props('flat')
                with self.account_closure_input.add_slot('append'):
                    ui.icon('edit_calendar').on('click', account_closure_menu.open).classes('cursor-pointer')
        with ui.column().classes("items-end w-full"):
            self.save_changes = ui.button("Save Changes", on_click=self.save_account_changes)

        self.budget_holder.disable()
        self.sysadmin.disable()
        self.finance_code.disable()
        self.task_code.disable()
        self.save_changes.disable()

    def save_account_changes(self):
        account: Account = Account.get(Account.id == self.account_id.text)
        selected_sysadmin = self.sysadmin.value
        if selected_sysadmin:
            selected_sysadmin = Person.get(Person.id == selected_sysadmin)
            Sysadmin.create(person=selected_sysadmin, account=account)
        else:
            account.sysadmin.get().delete_instance()
        selected_budgetholder = self.budget_holder.value
        if selected_budgetholder:
            selected_budgetholder = Person.get(Person.id == selected_budgetholder)
            account.budget_holder = selected_budgetholder
        else:
            account.budget_holder = None
        ui.notify("Record updated.")
        account.finance_code = self.finance_code.value
        account.task_code = self.task_code.value
        account.creation_date = datetime.date.fromisoformat(self.account_creation_date.value)
        account.closure_date = datetime.date.fromisoformat(self.account_closure_date.value)
        account.save()

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
        self.save_changes.disable()
        self.parent.notes.clear()

    def update(self, account: Account):
        self.sysadmin.enable()
        self.budget_holder.enable()
        self.finance_code.enable()
        self.task_code.enable()
        self.save_changes.enable()

        self.account_name.set_text(account.name)
        self.account_id.set_text(account.id)
        self.root_email.set_text(account.email)
        self.account_status.set_text(account.status)

        all_people = {person.id: person.full_name for person in Person.select()}
        self.budget_holder.set_options(all_people)
        self.sysadmin.set_options(all_people)

        self.finance_code.set_value(account.finance_code)
        self.task_code.set_value(account.task_code)

        if account.budget_holder:
            self.budget_holder.set_value(account.budget_holder.id)
        else:
            self.budget_holder.set_value(None)

        sysadmin = account.sysadmin.get_or_none()
        if sysadmin:
            self.sysadmin.set_value(sysadmin.person.id)
        else:
            self.sysadmin.set_value(None)

        if account.creation_date:
            self.account_creation_date.value = account.creation_date.isoformat()
        else:
            self.account_creation_input.value = ""

        if account.closure_date:
            self.account_closure_date.value = account.closure_date.isoformat()
        else:
            self.account_closure_date.value = ""

class UIAccountNotes:
    def __init__(self, parent: UIMainForm):
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

    def clear(self):
        self.notes_grid.options["rowData"] = {}
        self.notes_grid.update()


class UIAccountSelect:
    def __init__(self, parent: UIMainForm):
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
