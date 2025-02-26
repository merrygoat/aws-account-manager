import datetime

from nicegui import ui

import aam.utilities
from aam.models import Month


def initialize():
    add_months()
    ui.input.default_props("dense outlined")
    ui.textarea.default_props("outlined")
    ui.select.default_props("outlined")
    ui.label.default_classes("place-content-center")

def add_months():
    """This adds a new Month when the app is started for the first time in a given month."""
    required_months = aam.utilities.get_months_between(datetime.date(2021, 1, 1), datetime.date.today())
    actual_months = [month.month_code for month in Month.select()]
    missing_months = set(required_months) - set(actual_months)

    for month_code in missing_months:
        Month.create(month_code=month_code, exchange_rate=1)
