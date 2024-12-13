import datetime

import aam.utilities
from aam.models import Person, Month


def initialize():
    add_people()
    add_months()

def add_people():
    people = [person for person in Person.select()]
    if not people:
        Person.create(first_name="Peter", last_name="Crowther", email="peter@internet.com")
        Person.create(first_name="Felix", last_name="Edelsten", email="felix@internet.com")
        Person.create(first_name="Connor", last_name="Main", email="connor@internet.com")

def add_months():
    """This adds a new Month when the app is started for the first time in a given month."""
    required_months = aam.utilities.get_months_between(datetime.date(2021, 1, 1), datetime.date.today())
    actual_months = [month.month_code for month in Month.select()]
    missing_months = set(required_months) - set(actual_months)

    for month_code in missing_months:
        Month.create(month_code=month_code, exchange_rate=1)
