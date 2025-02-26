import datetime
from typing import TYPE_CHECKING, Iterable

import nicegui.events
from nicegui import ui

from aam.models import Note

if TYPE_CHECKING:
    from aam.main import UIAccountDetails


class UIAccountNotes:
    def __init__(self, parent: "UIAccountDetails"):
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
        self.add_note_dialog = AddNoteDialog(self)
        self.edit_note_dialog = EditNoteDialog(self)
        with ui.row():
            ui.button('Add note', on_click=self.add_note_button_press)
            ui.button('Edit note', on_click=self.edit_note_button_press)

    def add_note_button_press(self, event: nicegui.events.ClickEventArguments):
        selected_account_id = self.parent.parent.get_selected_account_id()
        if selected_account_id is not None:
            self.add_note_dialog.open(selected_account_id)
        else:
            ui.notify("No account selected to add note.")

    async def edit_note_button_press(self, event: nicegui.events.ClickEventArguments):
        selected_account = self.parent.parent.get_selected_account_id()
        if selected_account is not None:
            note_row = await(self.notes_grid.get_selected_row())
            if note_row:
                self.edit_note_dialog.open(note_row["id"])
            else:
                ui.notify("No note selected to edit.")
        else:
            ui.notify("No account selected to edit note.")

    def update_note_grid(self):
        account_id = self.parent.parent.get_selected_account_id()

        if account_id is None:
            self.clear()
            return 0

        notes: Iterable[Note] = Note.select().where(Note.account == account_id)
        if notes:
            note_details = [{"id": note.id, "date": note.date, "text": note.text} for note in notes]
        else:
            note_details = []
        self.notes_grid.options["rowData"] = note_details
        self.notes_grid.update()

    def clear(self):
        self.notes_grid.options["rowData"] = {}
        self.notes_grid.update()


class AddNoteDialog:
    def __init__(self, parent: "UIAccountNotes"):
        self.parent = parent
        self.selected_account_id: str | None = None

        with ui.dialog() as self.dialog:
            with ui.card():
                ui.html("Add Note").classes("text-2xl")
                with ui.input('Date',
                              value=datetime.datetime.today().strftime("%d/%m/%y"),
                              validation={"Must provide date": lambda value: len(value) > 1}
                              ) as self.date:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(mask="DD-MM-YY").bind_value(self.date):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with self.date.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')
                self.text = ui.textarea().classes('w-full')
                with ui.row():
                    ui.button("Save note", on_click=self.save_new_note)
                    ui.button("Cancel", on_click=self.close)

    def save_new_note(self, event: nicegui.events.ClickEventArguments):
        date = self.date.value
        text = self.text.value
        Note.create(date=date, text=text, account=self.selected_account_id)
        self.close()
        self.parent.update_note_grid()
        ui.notify("New Note saved.")

    def open(self, selected_account: str):
        self.selected_account_id = selected_account
        self.dialog.open()

    def close(self):
        self.dialog.close()


class EditNoteDialog:
    def __init__(self, parent: "UIAccountNotes"):
        self.parent = parent
        self.note_id = ""

        with ui.dialog() as self.dialog:
            with ui.card():
                ui.html("Edit Note").classes("text-2xl")
                with ui.input('Date', validation={"Must provide date": lambda value: len(value) > 1}) as self.date_input:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(mask="DD-MM-YY").bind_value(self.date_input):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with self.date_input.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')
                self.text = ui.textarea().classes('w-full')
                with ui.row():
                    ui.button("Save note", on_click=self.save_edit)
                    ui.button("Delete note", on_click=self.delete_note)
                    ui.button("Cancel", on_click=self.close)

    def close(self):
        self.dialog.close()

    def open(self, note_id: int):
        self.note_id = note_id

        note: Note = Note.get(id=note_id)
        self.date_input.value = note.date
        self.text.value = note.text
        self.dialog.open()

    def delete_note(self, event: nicegui.events.ClickEventArguments):
        Note.delete().where(Note.id == self.note_id).execute()
        self.parent.update_note_grid()
        self.close()
        ui.notify("Note deleted")

    def save_edit(self, event: nicegui.events.ClickEventArguments):
        date = self.date_input.value
        if not date:
            ui.notify("Must input date.")
            return 0
        try:
            date = datetime.date.fromisoformat(date)
        except ValueError as e:
            ui.notify(f"Note date is not valid: {e.args[0]}")
            return 0

        existing_note_id = self.note_id
        existing_note: Note = Note.get(id=existing_note_id)
        existing_note.text = self.text.value
        existing_note.date = date
        existing_note.save()
        self.parent.update_note_grid()
        self.close()
        ui.notify("Changes to Note saved.")
