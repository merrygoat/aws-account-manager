import datetime
from typing import TYPE_CHECKING, Iterable, Optional

import nicegui.events
from nicegui import ui

from aam.models import Note

if TYPE_CHECKING:
    from aam.main import UIAccountDetails


class UIAccountNotes:
    def __init__(self, parent: "UIAccountDetails"):
        self.parent = parent

        self.add_note_dialog = AddNoteDialog(self)

        ui.html("Notes").classes("text-xl")
        self.notes_grid = ui.aggrid({
            'columnDefs': [{"headerName": "id", "field": "id", "hide": True},
                           {"headerName": "Date", "field": "date", "editable": True},
                           {"headerName": "Type", "field": "type"},
                           {"headerName": "Note", "field": "text", "width": "flex"}],
            'rowData': {},
            'rowSelection': 'multiple',
            'stopEditingWhenCellsLoseFocus': True,
        })
        self.note_text = ui.textarea().classes("w-full").props('input-class=h-96')
        with ui.row().classes("w-full"):
            ui.space()
            ui.button('Add note', on_click=self.add_note_button_press)
            ui.button('Save note', on_click=self.save_note)
            ui.button('Delete note', on_click=self.delete_note)
        self.notes_grid.on("cellClicked", self.note_selected)
        self.notes_grid.on("cellValueChanged", self.update_note)

    async def get_selected_note(self) -> Optional[Note]:
        note_row = await(self.notes_grid.get_selected_row())
        if not note_row:
            return None
        note_id = note_row["id"]
        note: Note = Note.get(Note.id == note_id)
        return note

    def note_selected(self, event: nicegui.events.GenericEventArguments):
        note: Note = Note.get(Note.id == event.args["data"]["id"])
        self.note_text.set_value(note.text)

    def add_note_button_press(self, _event: nicegui.events.ClickEventArguments):
        selected_account_id = self.parent.parent.get_selected_account_id()
        if selected_account_id is not None:
            self.add_note_dialog.open(selected_account_id)
        else:
            ui.notify("No account selected to add note.")

    def update_note(self, event: nicegui.events.GenericEventArguments):
        """When an edit is made to a row in the note grid, save the changes to the database."""
        valid_cell_types = ["date"]
        note_id = event.args["data"]["id"]
        cell_edited = event.args["colId"]


        if cell_edited not in valid_cell_types:
            ui.notify(f"Unable to edit cell type '{cell_edited}'")
            return 0

        note: Note = Note.get(Note.id == note_id)

        if cell_edited == "date":
            if note.type == "Internal":
                note.date = datetime.date.fromisoformat(event.args["data"]["date"])
            else:
                ui.notify(f"Unable to change date for note type: '{note.type}'")
                return 0

        note.save()
        ui.notify(f"Note {cell_edited} edited.")
        self.update_note_grid()


    async def delete_note(self):
        note = await(self.get_selected_note())
        if note is None:
            ui.notify("No note selected to delete.")
            return 0

        if note.type != "Internal":
            ui.notify(f"Can not delete notes of type '{note.type}'")
            return 0

        note.delete_instance()
        self.update_note_grid()
        ui.notify("Note deleted.")


    async def save_note(self, _event: nicegui.events.ClickEventArguments):
        selected_account = self.parent.parent.get_selected_account_id()
        if selected_account is None:
            ui.notify("No account selected to edit note.")
            return 0

        note = await(self.get_selected_note())
        if note is None:
            ui.notify("No note selected to edit.")
            return 0

        if note.type != "Internal":
            ui.notify(f"Can not modify notes of type '{Note.type}'")
            return 0

        note.text = self.note_text.value
        note.save()
        ui.notify("Note text saved.")

    def update_note_grid(self):
        self.note_text.set_value("")

        account_id = self.parent.parent.get_selected_account_id()
        if account_id is None:
            self.clear()
            return 0

        notes: Iterable[Note] = Note.select().where(Note.account == account_id)
        if notes:
            note_details = [{"id": note.id, "date": note.date, "type": note.type, "text": note.text} for note in notes]
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

    def save_new_note(self, _event: nicegui.events.ClickEventArguments):
        date = datetime.date.fromisoformat(self.date.value)
        text = self.text.value
        Note.create(date=date, text=text, account=self.selected_account_id, type="Internal")
        self.close()
        self.parent.update_note_grid()
        ui.notify("New Note saved.")

    def open(self, selected_account: str):
        self.selected_account_id = selected_account
        self.dialog.open()

    def close(self):
        self.dialog.close()
