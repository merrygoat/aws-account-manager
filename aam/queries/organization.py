import sqlalchemy.exc

from aam.db import db_instance
from aam.models import Organization
from aam.utilities import Result


def get_all_organizations() -> list[Organization]:
    organizations = Organization.query.all()
    return organizations


def add_new_organization(json: dict) -> Result:
    new_organization = Organization(name=json["name"])
    db_instance.session.add(new_organization)
    try:
        db_instance.session.commit()
    except sqlalchemy.exc.IntegrityError:
        return Result(False, {"error": "Organization not added. Unknown error."})
    return Result(True, {"id": new_organization.id})


def delete_organization(json: dict):
    Organization.query.filter_by(id=json["id"]).delete()
    db_instance.session.commit()
    return Result(True, {})


def edit_organization(record: dict):
    organization = Organization.query.filter_by(id=record["id"]).first()
    organization.name = record["name"]
    db_instance.session.commit()
    return Result(True, {})
