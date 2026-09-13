from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.core.db import Base


class AuditLog(Base):
    """Append-only: nothing in this codebase should ever UPDATE or DELETE
    a row here (see 감사 로그 정책). No updated_at — a log entry is never
    edited after it is written."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    actor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action = Column(String, nullable=False)  # VIEW / CREATE / UPDATE / APPROVE / REJECT
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=False)
    # Nullable + SET NULL: not every audited action is patient-scoped (e.g. a
    # login event), and a log entry must never block a Patient from being
    # removed nor disappear itself if that ever happened.
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reason = Column(String, nullable=False)  # e.g. "assigned_patient", "self", "admin"
    created_at = Column(DateTime(timezone=True), nullable=False)
