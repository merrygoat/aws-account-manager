from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from db import db_instance


class Organization(db_instance.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)

    def __repr__(self):
        return self.name


class Account(db_instance.Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(150), nullable=False)
    organization_id = Column(Integer, ForeignKey('organization.id'), nullable=False)
    organization = relationship("Organization")

    def __repr__(self):
        return self.full_name
