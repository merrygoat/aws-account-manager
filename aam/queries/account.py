from aam import db
from aam.models import Account
from aam.queries import organization
from aam.utilities import Result


def get_all_accounts() -> list[Account]:
    return db.session.execute(db.select(Account)).scalars().all()


def get_account_by_id(account_id: int) -> Account:
    return db.session.execute(db.select(Account).filter_by(id=account_id)).scalar_one()


def add_new_account(json: dict) -> Result:
    # Remove the placeholder id so that one is assigned by the DB.
    json.pop("id")
    if "organization" in json:
        json["organization"] = organization.get_organization_by_name(json["organization"])
    new_account = Account(**json)
    db.session.add(new_account)
    try:
        db.session.commit()
    except Exception as e:
        print(e)
        return Result(False, {"error": "Organization not added. Unknown error."})
    return Result(True, {"id": new_account.id})


def edit_account(record: dict) -> Result:
    account = get_account_by_id(record["id"])
    account.organization = organization.get_organization_by_name(record.pop("organization"))
    for key, value in record.items():
        setattr(account, key, value)
    db.session.commit()
    return Result(True, {})


def delete_account(json: dict) -> Result:
    account = get_account_by_id(json["id"])
    db.session.delete(account)
    db.session.commit()
    return Result(True, {})
