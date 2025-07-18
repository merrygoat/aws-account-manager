import calendar
import datetime
import re
from typing import Optional

from nicegui import ui


def get_months_between(start_date: datetime.date, end_date: datetime.date) -> list[int]:
    start_date = start_date.year * 12 + start_date.month
    end_date = end_date.year * 12 + end_date.month
    return list(range(start_date, end_date + 1))


def date_picker(initial_value: datetime.date = None) -> ui.input:
    with ui.input(validation=lambda value: 'Invalid format' if (len(value) > 1) & (re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None) else None).props("dense") as date_input:
        with ui.menu().props('no-parent-event') as account_creation_menu:
            with ui.date().bind_value(date_input):
                with ui.row().classes('justify-end'):
                    ui.button('Close', on_click=account_creation_menu.close).props('flat')
        with date_input.add_slot('append'):
            ui.icon('edit_calendar').on('click', account_creation_menu.open).classes('cursor-pointer')
    if initial_value:
        date_input.value = initial_value.strftime("%Y-%m-%d")

    return date_input

class MonthYearPicker:
    """A custom gui element which adds two select elements to allow picking a month and a year."""
    def __init__(self, vertical: bool = False) -> None:
        with ui.row():
            self._month = month_select()
            self._year = year_select()

    @property
    def month(self) -> Optional[int]:
        if self._month.value:
            return self._month.value
        else:
            return None

    @property
    def year(self) -> Optional[int]:
        if self._year.value:
            return int(self._year.value)
        else:
            return None

    @property
    def month_code(self) -> Optional[int]:
        if self._month.value and self._year.value:
            return month_code(self._year.value, self._month.value)
        else:
            return None

    def set_visibility(self, visible: bool):
        if visible:
            self._month.set_visibility(True)
            self._year.set_visibility(True)
        else:
            self._month.set_visibility(False)
            self._year.set_visibility(False)

    def set_value(self, month: int, year: int):
        self._month.set_value(month)
        self._year.set_value(year)


def month_select() -> ui.select:
    return ui.select(options={index + 1: month for index, month in enumerate(calendar.month_abbr[1:])}, label="Month").props("dense").classes("min-w-[120px]")


def year_select() -> ui.select:
    return ui.select(options=list(range(2021, datetime.date.today().year + 1)), label="Year").props("dense").classes("min-w-[120px]")


def month_code(year: int, month: int) -> int:
    return year * 12 + month


def year_from_month_code(code: int) -> int:
    return (code - 1) // 12


def month_from_month_code(code: int) -> int:
    month = code % 12
    if month == 0:
        month = 12
    return month


def date_from_month_code(code: int) -> datetime.date:
    return datetime.date(year_from_month_code(code), month_from_month_code(code), 1)


def load_icon() -> str:
    with open("aam/static/icon.svg", 'r') as input_file:
        return input_file.read()
