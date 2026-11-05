from datetime import date, datetime

from pydantic import BaseModel


class TimelinePatientOut(BaseModel):
    id: int
    mrn: str
    name: str
    birth_date: date


class TimelineItemOut(BaseModel):
    """6개 event_type(ENCOUNTER/DIAGNOSIS/LAB_RESULT/PRESCRIPTION/
    CLINICAL_NOTE/VITAL_SIGN)이 공유하는 평평한(flat) 타임라인 항목
    스키마.

    source_type은 ENCOUNTER 항목에서는 null이다 — Encounter 모델 자체에는
    source_type 필드가 없기 때문이다(요건 명시 사항).

    Task F4-A: vital_type/value/value_secondary/unit/quality_warnings는
    event_type="VITAL_SIGN"일 때만 값이 있고, 그 외 5개 event_type에서는
    전부 null/빈 배열이다(기존 응답에 추가되는 신규 필드 — 기존 5개
    event_type의 의미는 전혀 바뀌지 않는다). value/value_secondary는
    Decimal을 그대로 JSON 문자열로 직렬화한다(정밀도 보존, 숫자 타입
    아님 — Frontend는 string으로 받는다).

    bmi는 event_type="ENCOUNTER"일 때만, 그 Encounter에서 BODY_HEIGHT와
    BODY_WEIGHT가 모두 canonical 단위로 존재해 계산 가능한 경우에만
    값이 있다(그 외에는 null). DB에 저장된 값이 아니라 조회 시점에
    매번 다시 계산한 파생값이다.
    """

    id: int
    encounter_id: int
    event_type: str
    event_time: datetime
    title: str
    summary: str
    source_type: str | None
    department: str
    vital_type: str | None = None
    value: str | None = None
    value_secondary: str | None = None
    unit: str | None = None
    quality_warnings: list[str] = []
    bmi: str | None = None


class PatientTimelineOut(BaseModel):
    patient: TimelinePatientOut
    timeline: list[TimelineItemOut]
