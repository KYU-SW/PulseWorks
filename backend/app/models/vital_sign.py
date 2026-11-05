from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, func

from app.core.db import Base
from app.models.enums import SourceType, VitalType


class VitalSign(Base):
    """활력징후(VitalSign) 1건. Task F4-A 범위 — Evidence Tag·Prompt·
    EmrSnapshot과는 아직 연결되지 않는다(F4-B에서 연결).

    patient_id를 따로 저장하지 않는다 — LabResult/Diagnosis/Prescription과
    같은 패턴으로 encounter_id 하나만 두고, 환자는 Encounter.patient_id를
    통해서만 알 수 있다(두 FK가 서로 다른 환자를 가리키는 불일치를
    구조적으로 막기 위함).

    value/value_secondary는 Numeric(10,3) — 기존 LabResult.value(Float)는
    그대로 두고 건드리지 않는다. BLOOD_PRESSURE는 value=수축기,
    value_secondary=이완기를 모두 채워야 하고(한쪽만 있으면 구조 오류),
    그 외 6종은 value만 채우고 value_secondary는 항상 NULL이어야 한다 —
    이 불변조건은 모델이 아니라 저장 시점에 애플리케이션(Pydantic 스키마·
    라우터)에서 검증한다(DB 제약으로 강제하지 않음 — SQLAlchemy 레벨
    CheckConstraint는 이번 범위에서 추가하지 않는다).
    """

    __tablename__ = "vital_signs"

    id = Column(Integer, primary_key=True)
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vital_type = Column(Enum(VitalType), nullable=False)
    value = Column(Numeric(10, 3), nullable=False)
    value_secondary = Column(Numeric(10, 3), nullable=True)
    unit = Column(String, nullable=False)
    measured_at = Column(DateTime(timezone=True), nullable=False)
    source_type = Column(Enum(SourceType), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
