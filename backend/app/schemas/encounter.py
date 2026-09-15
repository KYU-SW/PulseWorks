from datetime import date, datetime

from pydantic import BaseModel


class TimelinePatientOut(BaseModel):
    id: int
    mrn: str
    name: str
    birth_date: date


class TimelineItemOut(BaseModel):
    """5개 event_type(ENCOUNTER/DIAGNOSIS/LAB_RESULT/PRESCRIPTION/
    CLINICAL_NOTE)이 공유하는 평평한(flat) 타임라인 항목 스키마.

    source_type은 ENCOUNTER 항목에서는 null이다 — Encounter 모델 자체에는
    source_type 필드가 없기 때문이다(요건 명시 사항).
    """

    id: int
    encounter_id: int
    event_type: str
    event_time: datetime
    title: str
    summary: str
    source_type: str | None
    department: str


class PatientTimelineOut(BaseModel):
    patient: TimelinePatientOut
    timeline: list[TimelineItemOut]
