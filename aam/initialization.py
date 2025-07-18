import datetime
import logging

from nicegui import ui
from authlib.integrations.starlette_client import OAuth

import aam.utilities
from aam.config import CONFIG
from aam.models import Month

oauth = OAuth()

def initialize():
    logging_init()
    add_months()
    if CONFIG['oauth']["auth"]:
        oauth_setup()
    ui.input.default_props("dense outlined")
    ui.textarea.default_props("outlined")
    ui.select.default_props("outlined")
    ui.label.default_classes("place-content-center")

def oauth_setup():
    # The value of the name parameter is arbitrary but is needed to call the methods of the OAuth object later.
    oauth.register(
        name="aam_oidc",
        server_metadata_url=CONFIG["oauth"]["metadata_url"],
        client_id=CONFIG['oauth']["oauth_client_id"],
        client_secret=CONFIG['oauth']["oauth_client_secret"],
        client_kwargs={'scope': 'openid email'},
    )

def add_months():
    """This adds a new Month when the app is started for the first time in a given month."""
    required_months = aam.utilities.get_months_between(datetime.date(2021, 1, 1), datetime.date.today())
    actual_months: list[Month] = [month for month in Month.select()]
    missing_months = set(required_months) - set([month.month_code for month in actual_months])

    for month_code in missing_months:
        Month.create(month_code=month_code, exchange_rate=1)

def logging_init():
    if CONFIG["debug"]:
        logger = logging.getLogger('peewee')
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)