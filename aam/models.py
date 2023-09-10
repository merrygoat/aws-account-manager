import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship

from aam.db import db_instance


class JsonMixin:
    def to_json(self):
        """Generates a dict of the attributes of an object, removing any prepended with an underscore and using the
        to_json method of any objects where possible."""
        attributes = self.__dict__
        processed_attributes = {}
        for key, value in attributes.items():
            if not key.startswith("_"):
                if "to_json" in dir(value):
                    processed_attributes.update(value.to_json())
                else:
                    processed_attributes[key] = value
        return processed_attributes


class Organization(db_instance.Model, JsonMixin):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    def __repr__(self):
        return self.name


class Person(db_instance.Model, JsonMixin):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(50), nullable=False)

    def __repr__(self):
        return self.name


class AccountStatus(enum.Enum):
    ACTIVE = 1
    SUSPENDED = 2
    UNKNOWN = 3

    def to_json(self):
        return {"account_status": self.name}


class Account(db_instance.Model, JsonMixin):
    id = Column(Integer, primary_key=True)
    account_id = Column(String(12))
    name = Column(String(150))
    organization_id = Column(Integer, ForeignKey('organization.id'))
    organization = relationship("Organization")
    status = Column(Enum(AccountStatus))
    num_MFA_devices = Column(Integer)
    email = Column(String(150))
    # business_owner_id = Column(Integer, ForeignKey('business_owner.id'))
    # business_owner = relationship("Person")
    # PO_number = Column(String)
    # notes = Column(String(1000))

    def __repr__(self):
        return self.full_name
