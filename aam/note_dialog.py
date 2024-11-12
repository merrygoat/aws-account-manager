import functools
from datetime import datetime

import nicegui.events
from nicegui import ui
from pygments.lexer import default

from aam.models import Note


def add_note_dialog(ui_elements: dict):
    account = ui_elements["grid"].get_selected_row()

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
            ui.button("Save note", on_click=functools.partial(save_note, ui_elements))
            ui.button("Delete note")
            ui.button("Cancel", on_click=lambda: ui_elements["note_dialog"].close())

async def save_note(ui_elements: dict, event: nicegui.events.ClickEventArguments):
    account_row = await(ui_elements["grid"].get_selected_row())
    account_id = account_row['id']
    date = ui_elements["add_note_date"].value
    text = ui_elements["add_note_text"].value
    Note.create(date=date, text=text, account_id=account_id)