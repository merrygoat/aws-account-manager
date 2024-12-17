import datetime
from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

from aam.models import Account, Person, Sysadmin

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIAccountDetails:
    def __init__(self, parent: "UIMainForm"):
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
            account.sysadmin = None
        selected_budgetholder = self.budget_holder.value
        if selected_budgetholder:
            selected_budgetholder = Person.get(Person.id == selected_budgetholder)
            account.budget_holder = selected_budgetholder
        else:
            account.budget_holder = None
        ui.notify("Record updated.")
        account.finance_code = self.finance_code.value
        account.task_code = self.task_code.value
        account_creation_date = self.account_creation_date.value
        if account_creation_date:
            account_creation_date = datetime.date.fromisoformat(account_creation_date)
        account.creation_date = account_creation_date

        account_closure_date = self.account_closure_date.value
        if account_closure_date:
            account_closure_date = datetime.date.fromisoformat(account_closure_date)
        account.closure_date = account_closure_date
        account.save()
        self.parent.bills.update_bill_grid()

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

    def update(self, account: Account | None):
        if account is None:
            self.clear()
            return 0

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
