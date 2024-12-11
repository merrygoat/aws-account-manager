from typing import TYPE_CHECKING

from nicegui import ui
import nicegui.events
from watchfiles.run import raise_keyboard_interrupt

from aam.models import Person

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIPeople:
    def __init__(self, parent: "UIMainForm"):
        self.parent = parent

        self.new_person_dialog = AddPersonDialog(self)

        with ui.row().classes('w-full no-wrap'):
            with ui.column().classes('w-1/4'):
                ui.html("Person details").classes("text-2xl")
                self.person_select = ui.select(options=[], label="Person", on_change=self.show_person_details).classes("min-w-[400px]").props('popup-content-class="!max-h-[500px]"')
                with ui.grid(columns="auto auto"):
                    ui.label("First Name").classes("place-content-center")
                    self.first_name = ui.input()
                    ui.label("Surname").classes("place-content-center")
                    self.last_name = ui.input()
                    ui.label("Email").classes("place-content-center")
                    self.email = ui.input()
            with ui.column().classes('w-1/2'):
                ui.html("Person roles").classes("text-2xl")
                self.roles_grid = ui.aggrid({
                    'defaultColDef': {"suppressMovable": True},
                    'columnDefs': [{"headerName": "Account", "field": "account", "sort": "desc"},
                                   {"headerName": "Role", "field": "role"}],
                    'rowData': {}})
        with ui.row():
            self.save_changes = ui.button("Save Changes", on_click=self.save_changes)
            self.add_new_person = ui.button("Add New Person", on_click=self.new_person_dialog.open)
            self.delete_person = ui.button("Delete Person", on_click=self.delete_person)

        self.populate_select()

    def save_changes(self, event: nicegui.events.ClickEventArguments):
        selected_person_id = self.person_select.value
        selected_person: Person = Person.get(id=selected_person_id)
        selected_person.first_name = self.first_name.value
        selected_person.last_name = self.last_name.value
        selected_person.email = self.email.value
        selected_person.save()
        ui.notify("Person details updated.")

    def populate_select(self):
        people = Person.select()
        people = {person.id: f"{person.first_name} {person.last_name}" for person in people}
        self.person_select.set_options(people)
        
    def show_person_details(self, event: nicegui.events.ValueChangeEventArguments):
        selected_person_id = event.sender.value
        person: Person = Person.get(Person.id == selected_person_id)
        self.first_name.value = person.first_name
        self.last_name.value = person.last_name
        self.email.value = person.email
        roles = []
        for sysadmin in person.sysadmin:
            roles.append({"role": "Sysadmin", "account": sysadmin.account.name})
        if hasattr(person, "budget_holder"):
            for account in person.budget_holder:
                roles.append({"role": "Budget Holder", "account": account.name})
        self.roles_grid.options["rowData"] = roles
        self.roles_grid.update()

    def delete_person(self, event: nicegui.events.ClickEventArguments):
        selected_person_id = self.person_select.value
        selected_person: Person = Person.get(id=selected_person_id)
        if selected_person.sysadmin or selected_person.budget_holder:
            ui.notify("Person has active roles. These must be removed before the person is deleted.")
        else:
            selected_person.delete_instance()
            self.populate_select()
            self.first_name.value = ""
            self.last_name.value = ""
            self.email.value = ""
            ui.notify("Person successfully deleted")

class AddPersonDialog:
    def __init__(self, parent: "UIPeople"):
        self.parent = parent

        with ui.dialog() as self.dialog:
            with ui.card():
                self.title = ui.html("Add Person").classes("text-2xl")
                with ui.grid(columns="auto auto"):
                    ui.label("First Name").classes("place-content-center")
                    self.first_name = ui.input()
                    ui.label("Surname").classes("place-content-center")
                    self.last_name = ui.input()
                    ui.label("Email").classes("place-content-center")
                    self.email = ui.input()
                with ui.row():
                    ui.button("Save Person", on_click=self.save_new_person)
                    ui.button("Cancel", on_click=self.close)

    async def save_new_person(self):
        Person.create(first_name=self.first_name.value, last_name=self.last_name.value, email=self.email.value)
        self.close()
        ui.notify("New Person saved.")
        self.parent.populate_select()

    def open(self):
        self.dialog.open()

    def close(self):
        self.dialog.close()
