from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey
from app.core.db import Base
from app.models.enums import Department, EncounterType


class Encounter(Base):
    __tablename__ = "encounters"

    id = Column(Integer, primary_key=True)
    # NOT NULL FK -> ON DELETE RESTRICT: an Encounter can never outlive (or be
    # orphaned from) its Patient.
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    department = Column(Enum(Department), nullable=False)
    encounter_type = Column(Enum(EncounterType), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
