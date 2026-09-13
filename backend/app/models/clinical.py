from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    func,
)
from app.core.db import Base
from app.models.enums import SourceType

# All six tables below carry `source_type` (patient_reported vs
# institution_generated — requirement 6) plus a pair of audit columns:
#   - created_at / updated_at: when this DB row itself was inserted/edited.
#   - the table's own domain timestamp (diagnosed_at, measured_at, ...):
#     when the clinical event itself happened, which is not always the same
#     instant as the row's insert time.
# ClinicalNote is the one exception: its only timestamp is `created_at`,
# which already serves as the domain timestamp (a note's authoring instant
# and its row-creation instant are the same event), so no second column is
# added there — only `updated_at` for later edits.


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    code = Column(String, nullable=False)
    description = Column(String, nullable=False)
    diagnosed_at = Column(DateTime(timezone=True), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    test_name = Column(String, nullable=False)
    ordered_at = Column(DateTime(timezone=True), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Nullable: a patient-reported self-measurement (source_type=
    # PATIENT_REPORTED) has no institution Order behind it.
    order_id = Column(
        Integer,
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_name = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    reference_low = Column(Float, nullable=False)
    reference_high = Column(Float, nullable=False)
    is_abnormal = Column(Boolean, nullable=False, default=False)
    measured_at = Column(DateTime(timezone=True), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    medication_name = Column(String, nullable=False)
    dosage = Column(String, nullable=False)
    prescribed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    prescribed_at = Column(DateTime(timezone=True), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    author_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    note_text = Column(String, nullable=False)
    # Doubles as the domain timestamp (when the note was written) — see
    # module docstring above for why this table has no separate field.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    source_type = Column(Enum(SourceType), nullable=False)


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(Integer, primary_key=True)
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    substance = Column(String, nullable=False)
    reaction = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
