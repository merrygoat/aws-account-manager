from typing import Optional

import sqlalchemy.exc

from aam.db import db
from aam.models import Organization
from aam.utilities import Result


def get_all_organizations() -> list[Organization]:
    return db.session.execute(db.select(Organization)).scalars().all()


def get_organization_by_name(name: str) -> Optional[Organization]:
    return db.session.execute(db.select(Organization).filter_by(name=name)).scalar_one_or_none()


def get_organization_by_id(org_id: int) -> Optional[Organization]:
    return db.session.execute(db.select(Organization).filter_by(id=org_id)).scalar_one()


def add_new_organization(json: dict) -> Result:
    new_organization = Organization(name=json["name"])
    db.session.add(new_organization)
    try:
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        return Result(False, {"error": "Organization not added. Unknown error."})
    return Result(True, {"id": new_organization.id})


def delete_organization(json: dict) -> Result:
    organization = get_organization_by_id(json["id"])
    db.session.delete(organization)
    db.session.commit()
    return Result(True, {})


def edit_organization(record: dict) -> Result:
    organization = get_organization_by_id(record["id"])
    organization.name = record["name"]
    db.session.commit()
    return Result(True, {})
