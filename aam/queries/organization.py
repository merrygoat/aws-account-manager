from typing import Optional

import sqlalchemy.exc

from aam.db import db
from aam.models import Organization
from aam.utilities import Result


def get_all_organizations() -> list[Organization]:
    organizations = Organization.query.all()
    return organizations


def get_organization_by_name(name: str) -> Optional[Organization]:
    return Organization.query.filter_by(name=name).first()


def add_new_organization(json: dict) -> Result:
    new_organization = Organization(name=json["name"])
    db.session.add(new_organization)
    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        return Result(False, {"error": "Organization not added. Unknown error."})
    return Result(True, {"id": new_organization.id})


def delete_organization(json: dict) -> Result:
    Organization.query.filter_by(id=json["id"]).delete()
    db.session.commit()
    return Result(True, {})


def edit_organization(record: dict) -> Result:
    organization = Organization.query.filter_by(id=record["id"]).first()
    organization.name = record["name"]
    db.session.commit()
    return Result(True, {})
