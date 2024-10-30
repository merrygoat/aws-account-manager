from nicegui import events, ui

import aam.models
from aam.models import Event


def open_edit_event_dialog(event: events.GenericEventArguments, ui_elements: dict):
    ui_elements["add_event_button"].set_visibility(False)
    ui_elements["update_event_button"].set_visibility(True)
    ui_elements["dialog_title"].text = "Edit Event"

    # Need this 'info' catch as an event click generates two different events, and we only want one of them
    if 'info' in event.args:
        clicked_event = event.args["info"]["event"]
        event_id = clicked_event["id"]

        event = Event.select().where(Event.id == event_id).get()
        for prop in aam.models.props:
            ui_elements[prop].set_value(getattr(event, prop))
        for prop in aam.models.extended_props:
            ui_elements[prop].set_value(getattr(event, prop))

        ui_elements["dialog"].open()


def open_add_event_dialog(ui_elements: dict):
    ui_elements["add_event_button"].set_visibility(True)
    ui_elements["update_event_button"].set_visibility(False)
    ui_elements["dialog_title"].text = "Add New Event"

    for prop, default_value in aam.models.all_props.items():
        ui_elements[prop].value = default_value

    ui_elements["dialog"].open()


def update_event(ui_elements: dict):
    if not validate_dialog(ui_elements):
        # Don't allow form completion if any element is invalid
        return False

    event_id = ui_elements["id"].value

    # Get the event and update it from the values in the dialog
    event = Event.select().where(Event.id == event_id).get()
    for prop in aam.models.all_props:
        event.__setattr__(prop, ui_elements[prop].value)
    event.save()

    ui_elements["month_calendar"].remove_event(event_id, update=False)
    ui_elements["month_calendar"].add_event(event.to_dict())

    ui_elements["dialog"].close()


def add_new_event(ui_elements):
    """Create a new Event object, add it to the calendar and close the dialog."""

    if not validate_dialog(ui_elements):
        # Don't allow form completion if any element is invalid
        return False

    event_details = {element_name: ui_elements[element_name].value for element_name in models.all_props}
    # id will be auto assigned by db - so don't specify it.
    event_details.pop("id")
    new_event = Event(**event_details)
    new_event.save()

    ui_elements["month_calendar"].add_event(new_event.to_dict())

    ui_elements["dialog"].close()


def validate_dialog(ui_elements: dict):
    elements_valid = []
    for prop, default_value in models.all_props.items():
        if "validate" in dir(ui_elements[prop]):
            elements_valid.append(ui_elements[prop].validate())
    if all(elements_valid):
        return True
    else:
        ui.notify('Some fields are invalid', type='negative')
        return False


def build_dialog(projects_list, ui_elements: dict):
    """Create the nicegui elements that make up the dialog box."""
    with ui.dialog() as ui_elements["dialog"], ui.card().classes():
        ui_elements["id"] = ui.input()
        ui_elements["id"].set_visibility(False)
        ui_elements["dialog_title"] = ui.label("Dialog Title").classes("text-xl text-center full-width")
        with ui.grid(columns='80px auto').classes('w-full'):
            ui.label("Title").classes('place-content-center')
            ui_elements["title"] = ui.input(validation={'Must provide title': lambda value: len(value) > 0})
            ui.label("Date").classes('place-content-center')
            with ui.input('Date', validation={'Must provide date': lambda value: len(value) > 0}) as ui_elements["start"]:
                with ui_elements["start"].add_slot('append'):
                    ui.icon('edit_calendar').on('click', lambda: menu.open()).classes('cursor-pointer')
                with ui.menu() as menu:
                    ui.date().bind_value(ui_elements["start"])
            ui.label("Project").classes('place-content-center')
            ui_elements["project"] = ui.select(projects_list, value=1, clearable=True, with_input=True)
            ui.label("Status").classes('place-content-center')
            ui_elements["status"] = ui.radio(["Scheduled", "Logged"]).props('inline')
            ui.label("Completed").classes('place-content-center')
            ui_elements["completed"] = ui.radio(["Yes", "No"], value="No").props('inline')
            ui.label("Repeating Event").classes('place-content-center')
            ui_elements["repeating"] = ui.radio(["Yes", "No"], value="No").props('inline')
        with ui.card() as repeat_card:
            repeat_card.bind_visibility_from(ui_elements["repeating"], "value", value="Yes")
            with ui.grid(columns='80px auto auto').classes('w-full'):
                ui.label("Repeat every").classes('place-content-center')
                ui_elements["repeat_interval"] = ui.select(list(range(1, 100)), value=1)
                ui_elements["repeat_frequency"] = ui.select(["Day", "Week", "Month"], value="Day").props("inline")

        with ui.row().classes('w-full q-mt-md'):
            ui.space()
            ui_elements["add_event_button"] = ui.button('Add New Event', on_click=lambda: add_new_event(ui_elements))
            ui_elements["update_event_button"] = ui.button('Update Event', on_click=lambda: update_event(ui_elements))
            ui.button('Cancel', on_click=lambda: ui_elements["dialog"].close())
