import sqlalchemy.exc

from aam import db_instance
from aam.models import Account
from aam.utilities import Result


def get_all_accounts() -> list[Account]:
    organizations = Account.query.all()
    return organizations


def add_new_account(json: dict) -> Result:
    # Remove the placeholder id so that one is assigned by the DB.
    json.pop("id")
    new_account = Account(**json)
    db_instance.session.add(new_account)
    try:
        db_instance.session.commit()
    except Exception as e:
        print(e)
        return Result(False, {"error": "Organization not added. Unknown error."})
    return Result(True, {"id": new_account.id})


def edit_account(record: dict) -> Result:
    organization = Account.query.filter_by(id=record["id"]).first()
    for key, value in record.items():
        setattr(organization, key, value)
    db_instance.session.commit()
    return Result(True, {})


def delete_account(json: dict) -> Result:
    Account.query.filter_by(id=json["id"]).delete()
    db_instance.session.commit()
    return Result(True, {})
