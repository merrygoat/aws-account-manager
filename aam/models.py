import enum

from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship

from aam.db import db_instance


class Organization(db_instance.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    def __repr__(self):
        return self.name

    def to_json(self):
        return {"id": self.id, "name": self.name}


class Person(db_instance.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    email = Column(String(50), nullable=False)

    def __repr__(self):
        return self.name


class AccountStatus(enum.Enum):
    ACTIVE = 1
    SUSPENDED = 2
    UNKNOWN = 3


class Account(db_instance.Model):
    id = Column(Integer, primary_key=True)
    account_id = Column(String(12), nullable=False)
    name = Column(String(150), nullable=False)
    organization_id = Column(Integer, ForeignKey('organization.id'))
    organization = relationship("Organization")
    status = Column(Enum(AccountStatus))
    num_MFA_devices = Column(Integer)
    email = Column(String(150), nullable=False)
    # business_owner_id = Column(Integer, ForeignKey('business_owner.id'))
    # business_owner = relationship("Person")
    PO_number = Column(String)
    notes = Column(String(1000))

    def __repr__(self):
        return self.full_name
