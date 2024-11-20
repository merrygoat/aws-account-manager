import datetime

from dateutil import rrule
from nicegui import ui


def get_bill_months(start_date: datetime.date, end_date: datetime.date) -> list[datetime.date]:
    start_date = datetime.date(start_date.year, start_date.month, 1)
    bill_months = [date.date() for date in (rrule.rrule(freq=rrule.MONTHLY, dtstart=start_date, until=end_date))]
    return bill_months

def date_picker() -> ui.input:
    with ui.input('Date').props("dense") as date_input:
        with ui.menu().props('no-parent-event') as account_creation_menu:
            with ui.date().bind_value(date_input):
                with ui.row().classes('justify-end'):
                    ui.button('Close', on_click=account_creation_menu.close).props('flat')
        with date_input.add_slot('append'):
            ui.icon('edit_calendar').on('click', account_creation_menu.open).classes('cursor-pointer')

    return date_input