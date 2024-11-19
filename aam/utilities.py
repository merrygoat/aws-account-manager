import datetime

from dateutil import rrule


def get_bill_months(start_date: datetime.date, end_date: datetime.date) -> list[datetime.date]:
    start_date = datetime.date(start_date.year, start_date.month, 1)
    bill_months = [date.date() for date in (rrule.rrule(freq=rrule.MONTHLY, dtstart=start_date, until=end_date))]
    return bill_months
