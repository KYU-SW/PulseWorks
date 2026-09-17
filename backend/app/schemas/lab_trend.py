from datetime import date, datetime

from pydantic import BaseModel


class LabTrendPatientOut(BaseModel):
    id: int
    mrn: str
    name: str
    birth_date: date


class LabTrendPointOut(BaseModel):
    """검사 추세 그래프/표의 한 점. test_name은 그룹(LabTrendGroupOut) 레벨에만
    있고 점마다 중복하지 않는다 — 응답 데이터 최소화."""

    value: float
    unit: str
    reference_low: float
    reference_high: float
    measured_at: datetime
    status: str
    rule_id: str
    encounter_id: int
    source_type: str


class LabTrendGroupOut(BaseModel):
    test_name: str
    unit: str
    points: list[LabTrendPointOut]


class PatientLabTrendsOut(BaseModel):
    patient: LabTrendPatientOut
    trends: list[LabTrendGroupOut]
