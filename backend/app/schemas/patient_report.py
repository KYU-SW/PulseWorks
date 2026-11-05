"""환자용 승인 보고서 응답 스키마 (Task 19).

app.schemas.clinical_report의 의사용 스키마(ClinicalReportOut 등)를
상속하거나 재사용하지 않는다 — 화이트리스트 방식으로, 환자에게 보여줄
필드만 처음부터 정의한다. 내부 PK(id), rule_id, source_type,
created_by_user_id/last_modified_by_user_id/reviewed_by_user_id,
handoff_note, source_record_ids, SafetyAlert, ClinicalNote는 이 파일
어디에도 필드로 존재하지 않는다 — "가져온 뒤 지우는" 방식이 아니라
"애초에 옮기지 않는" 방식이다.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class PatientReportListItem(BaseModel):
    id: int
    report_type: str
    department: str
    encounter_date: date
    reviewed_at: datetime


class PatientDiagnosisOut(BaseModel):
    description: str
    diagnosed_at: datetime


class PatientLabResultOut(BaseModel):
    test_name: str
    value: float
    unit: str
    reference_low: float
    reference_high: float
    measured_at: datetime
    status: str


class PatientLabTrendPointOut(BaseModel):
    value: float
    unit: str
    reference_low: float
    reference_high: float
    measured_at: datetime
    status: str


class PatientLabTrendGroupOut(BaseModel):
    test_name: str
    unit: str
    points: list[PatientLabTrendPointOut]


class PatientPrescriptionOut(BaseModel):
    medication_name: str
    dosage: str
    prescribed_at: datetime


class PatientAllergyOut(BaseModel):
    substance: str
    reaction: str
    severity: str


class PatientVitalSignOut(BaseModel):
    """Task F4-B: 화이트리스트 방식 — vital_type/value/value_secondary/unit/
    measured_at만 노출한다. 품질 경고(quality_warnings), BMI, V Evidence
    Tag, source_record_id, 내부 DB id는 이 클래스 어디에도 필드로 존재하지
    않는다."""

    vital_type: str
    value: Decimal
    value_secondary: Decimal | None
    unit: str
    measured_at: datetime


class PatientClinicalReportDetail(BaseModel):
    id: int
    department: str
    # Task 18 의학용어 연결(환자용 진료 형태) 지점이라 최소 필드 목록에
    # 없었지만 상세 응답에 추가했다 — 목록 응답에는 필요 없어 넣지 않는다.
    encounter_type: str
    encounter_date: date
    reviewed_at: datetime
    narrative: str | None
    patient_guidance: str | None
    diagnoses: list[PatientDiagnosisOut]
    lab_results: list[PatientLabResultOut]
    lab_trends: list[PatientLabTrendGroupOut]
    prescriptions: list[PatientPrescriptionOut]
    allergies: list[PatientAllergyOut]
    vital_signs: list[PatientVitalSignOut]
    evidence: list[str]
    safety_notice: str
