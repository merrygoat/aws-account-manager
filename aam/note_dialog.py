import functools
from datetime import datetime

import nicegui.events
from nicegui import ui

from aam.models import Note


def add_note_dialog(ui_elements: dict):
    with ui.dialog() as ui_elements["note_dialog"], ui.card():
        ui.html("Add Note").classes("text-2xl")
        with ui.input('Date',
                      value=datetime.today().strftime("%d/%m/%y"),
                      validation={"Must provide date": lambda value: len(value) > 1}
                      ) as ui_elements["add_note_date"]:
            with ui.menu().props('no-parent-event') as menu:
                with ui.date(mask="DD-MM-YY").bind_value(ui_elements["add_note_date"]):
                    with ui.row().classes('justify-end'):
                        ui.button('Close', on_click=menu.close).props('flat')
            with ui_elements["add_note_date"].add_slot('append'):
                ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')
        ui_elements["add_note_text"] = ui.textarea().props('outlined').classes('w-full')
        with ui.row():
            ui.button("Save note", on_click=functools.partial(save_new_note, ui_elements))
            ui.button("Cancel", on_click=lambda: ui_elements["note_dialog"].close())

async def open_edit_note_dialog(ui_elements: dict, event: nicegui.events.ClickEventArguments):
    note_row = await(ui_elements["notes_grid"].get_selected_row())
    if note_row:
        note_id = note_row["id"]
        note = Note.get(id=note_id)
        ui_elements["edit_note_id"].text = note.id
        ui_elements["edit_note_date"].value = note.date
        ui_elements["edit_note_text"].value = note.text
        ui_elements["edit_note_dialog"].open()
    else:
        ui.notify("No note selected to edit.")

def edit_note_dialog(ui_elements: dict):
    with ui.dialog() as ui_elements["edit_note_dialog"], ui.card():
        ui_elements["edit_note_id"] = ui.label("")
        ui_elements["edit_note_id"].set_visibility(False)
        ui.html("Edit Note").classes("text-2xl")
        with ui.input('Date', validation={"Must provide date": lambda value: len(value) > 1}) as ui_elements[
            "edit_note_date"]:
            with ui.menu().props('no-parent-event') as menu:
                with ui.date(mask="DD-MM-YY").bind_value(ui_elements["add_note_date"]):
                    with ui.row().classes('justify-end'):
                        ui.button('Close', on_click=menu.close).props('flat')
            with ui_elements["add_note_date"].add_slot('append'):
                ui.icon('edit_calendar').on('click', menu.open).classes('cursor-pointer')
        ui_elements["edit_note_text"] = ui.textarea().props('outlined').classes('w-full')
        with ui.row():
            ui.button("Save note", on_click=functools.partial(edit_note, ui_elements))
            ui.button("Delete note", on_click=functools.partial(delete_note, ui_elements))
            ui.button("Cancel", on_click=lambda: ui_elements["edit_note_dialog"].close())

def delete_note(ui_elements: dict, event: nicegui.events.ClickEventArguments):
    ui_elements["note_dialog"].close()

def edit_note(ui_elements: dict, event: nicegui.events.ClickEventArguments):
    existing_note_id = ui_elements["edit_note_id"].text
    existing_note = Note.get(id=existing_note_id)
    existing_note.text = ui_elements["edit_note_text"].value
    existing_note.date = ui_elements["edit_note_date"].value
    existing_note.save()
    ui_elements["edit_note_dialog"].close()
    ui.notify("Changes to Note saved.")


async def save_new_note(ui_elements: dict, event: nicegui.events.ClickEventArguments):
    account_row = await(ui_elements["grid"].get_selected_row())
    account_id = account_row['id']
    date = ui_elements["add_note_date"].value
    text = ui_elements["add_note_text"].value
    Note.create(date=date, text=text, account_id=account_id)
    ui_elements["note_dialog"].close()
    ui.notify("New Note saved.")