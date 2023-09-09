import sqlalchemy.exc

from aam.db import db_instance
from aam.models import Account
from aam.utilities import Result


def get_all_accounts() -> list[Account]:
    organizations = Account.query.all()
    return organizations
