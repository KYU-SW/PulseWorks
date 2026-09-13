from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey, JSON
from app.core.db import Base
from app.models.enums import AiSummaryStatus


class AiSummary(Base):
    __tablename__ = "ai_summaries"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status = Column(Enum(AiSummaryStatus), nullable=False, default=AiSummaryStatus.DRAFT)
    summary_text = Column(String, nullable=False)
    source_record_ids = Column(JSON, nullable=False)  # e.g. ["lab_result:12", "clinical_note:5"]
    generated_at = Column(DateTime(timezone=True), nullable=False)
    reviewed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
