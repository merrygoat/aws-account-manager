import sqlalchemy.exc
import jsonpickle

from aam.db import db_instance
from aam.models import Organization
from aam.utilities import Result


def get_all_organizations() -> list[dict]:
    organizations = Organization.query.all()
    return [org.to_json() for org in organizations]


def add_new_organization(json: dict) -> Result:
    new_organization = Organization(name=json["name"])
    db_instance.session.add(new_organization)
    try:
        db_instance.session.commit()
    except sqlalchemy.exc.IntegrityError:
        return Result(False, "Organization not added. Unknown error.")
    return Result(True, str(new_organization.id))


def delete_organization(record_id: int):
    Organization.query.filter_by(id=record_id).delete()
    db_instance.session.commit()


def edit_organization(record_id: int, json: dict):
    organization = Organization.query.filter_by(id=record_id).first()
    organization.name = json["name"]
    db_instance.session.commit()
    return Result(True, "")
