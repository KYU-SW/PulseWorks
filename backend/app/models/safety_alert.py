from sqlalchemy import (
    CheckConstraint,
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
)
from app.core.db import Base
from app.models.enums import SafetyAlertPriority


class SafetyAlert(Base):
    __tablename__ = "safety_alerts"
    __table_args__ = (
        # A safety alert without any evidence link is meaningless — it must
        # point at the prescription and/or lab result that triggered it.
        CheckConstraint(
            "prescription_id IS NOT NULL OR lab_result_id IS NOT NULL",
            name="ck_safety_alert_has_evidence_link",
        ),
    )

    id = Column(Integer, primary_key=True)
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    prescription_id = Column(
        Integer,
        ForeignKey("prescriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lab_result_id = Column(
        Integer,
        ForeignKey("lab_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_id = Column(String, nullable=False)  # e.g. "ALLERGY_DRUG_CONFLICT"
    evidence = Column(JSON, nullable=False)
    priority = Column(Enum(SafetyAlertPriority), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
