import enum
from typing import List

from sqlalchemy import Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column

from aam.db import db


class JsonMixin:
    def to_json(self):
        """Generates a dict of the attributes of an object, removing any prepended with an underscore and using the
        to_json method of any objects where possible."""
        attributes = vars(self)
        processed_attributes = {}
        for key, value in attributes.items():
            if not key.startswith("_"):
                if "json_repr" in dir(value):
                    processed_attributes.update(value.json_repr())
                else:
                    processed_attributes[key] = value
        return processed_attributes


class Organization(db.Model, JsonMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    accounts: Mapped[List["Account"]] = relationship(back_populates="organization")

    def __repr__(self):
        return self.name

    def json_repr(self):
        """Return a representation of the object in JSON format."""
        return {"organization": self.name}


class Person(db.Model, JsonMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[str] = mapped_column(String(50))

    def __repr__(self):
        return self.name


class AccountStatus(enum.Enum):
    ACTIVE = 1
    SUSPENDED = 2
    UNKNOWN = 3

    def json_repr(self):
        return {"account_status": self.name}


class Account(db.Model, JsonMixin):
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(12))
    name: Mapped[str] = mapped_column(String(150))
    organization_id: Mapped[int] = mapped_column(ForeignKey('organization.id'))
    organization: Mapped[Organization] = relationship(back_populates="accounts", lazy="selectin")
    account_status: Mapped[Enum] = mapped_column(Enum(AccountStatus))
    num_MFA_devices: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String(150))
    # business_owner_id = Column(Integer, ForeignKey('business_owner.id'))
    # business_owner = relationship("Person")
    # PO_number = Column(String)
    # notes = Column(String(1000))

    def __repr__(self):
        return self.full_name
