import functools
from datetime import datetime
from typing import TYPE_CHECKING

import nicegui.events
from nicegui import ui

from aam.models import Note, Account

if TYPE_CHECKING:
    from aam.main import UIMainForm


class UIAccountNotes:
    def __init__(self, parent: "UIMainForm"):
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


class AddNoteDialog:
    def __init__(self, parent: "UIAccountNotes"):
        self.parent = parent

        with ui.dialog() as self.dialog:
            with ui.card():
                self.title = ui.html("Add Note").classes("text-2xl")
                with ui.input('Date',
                              value=datetime.today().strftime("%d/%m/%y"),
                              validation={"Must provide date": lambda value: len(value) > 1}
                              ) as self.date:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(mask="DD-MM-YY").bind_value(self.date):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with self.date.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')
                self.text = ui.textarea().props('outlined').classes('w-full')
                with ui.row():
                    ui.button("Save note", on_click=functools.partial(self.save_new_note, self.parent))
                    ui.button("Cancel", on_click=self.close)

    async def save_new_note(self, ui_elements: dict, event: nicegui.events.ClickEventArguments):
        account_row = await(ui_elements["grid"].get_selected_row())
        account_id = account_row['id']
        date = self.date.value
        text = self.text.value
        Note.create(date=date, text=text, account_id=account_id)
        self.close()
        ui.notify("New Note saved.")

    def open(self):
        self.dialog.open()

    def close(self):
        self.dialog.close()


class EditNoteDialog:
    def __init__(self, parent: "UIAccountNotes"):
        self.parent = parent
        self.note_id = ""

        with ui.dialog() as self.dialog:
            with ui.card():
                self.title = ui.html("Edit Note").classes("text-2xl")
                with ui.input('Date', validation={"Must provide date": lambda value: len(value) > 1}) as self.date_input:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date(mask="DD-MM-YY").bind_value(self.date_input):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with self.date_input.add_slot('append'):
                        ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')
                self.text = ui.textarea().props('outlined').classes('w-full')
                with ui.row():
                    ui.button("Save note", on_click=self.save_edit)
                    ui.button("Delete note", on_click=self.delete_note)
                    ui.button("Cancel", on_click=self.close)

    def close(self):
        self.dialog.close()

    async def open(self, event: nicegui.events.ClickEventArguments):
        note_row = await(self.parent.notes_grid.get_selected_row())
        if note_row:
            note_id = note_row["id"]
            note = Note.get(id=note_id)
            self.note_id = note.id
            self.date_input.value = note.date
            self.text.value = note.text
            self.dialog.open()
        else:
            ui.notify("No note selected to edit.")

    def delete_note(self, event: nicegui.events.ClickEventArguments):
        self.close()

    def save_edit(self, event: nicegui.events.ClickEventArguments):
        existing_note_id = self.note_id
        existing_note = Note.get(id=existing_note_id)
        existing_note.text = self.text.value
        existing_note.date = self.date_input.value
        existing_note.save()
        self.close()
        ui.notify("Changes to Note saved.")
