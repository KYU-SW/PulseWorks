from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.enums import ClinicalReportScopeType, ClinicalReportType

# --- emr_snapshot 하위 스키마 -------------------------------------------
# Task 12 app/services/report_data.py의 frozen dataclass들을 1:1로
# 미러링한다. from_attributes=True라서 그 dataclass 인스턴스를 그대로
# model_validate()에 넘길 수 있다.


class SnapshotPatient(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mrn: str
    name: str
    birth_date: date


class SnapshotEncounter(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department: str
    encounter_type: str
    start_time: datetime
    end_time: datetime | None


class SnapshotDiagnosis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    encounter_id: int
    code: str
    description: str
    diagnosed_at: datetime
    source_type: str


class SnapshotLabResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    encounter_id: int
    test_name: str
    value: float
    unit: str
    reference_low: float
    reference_high: float
    measured_at: datetime
    source_type: str
    status: str
    rule_id: str


class SnapshotLabTrendPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    value: float
    unit: str
    reference_low: float
    reference_high: float
    measured_at: datetime
    status: str
    rule_id: str
    encounter_id: int
    source_type: str


class SnapshotLabTrendGroup(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    test_name: str
    unit: str
    points: list[SnapshotLabTrendPoint]


class SnapshotPrescription(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    encounter_id: int
    medication_name: str
    dosage: str
    prescribed_by_user_id: int
    prescribed_at: datetime
    source_type: str


class SnapshotAllergy(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    substance: str
    reaction: str
    severity: str
    recorded_at: datetime
    source_type: str


class SnapshotSafetyAlert(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    encounter_id: int
    prescription_id: int | None
    lab_result_id: int | None
    rule_id: str
    priority: str
    evidence: dict
    created_at: datetime


class SnapshotClinicalNote(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    encounter_id: int
    author_user_id: int
    preview_text: str
    created_at: datetime
    source_type: str


class EmrSnapshot(BaseModel):
    """Task 12 ReportData 전체를 미러링한 구조화 원본 스냅샷. 이 안의
    필드는 보고서 PATCH(Task 17)의 대상이 아니다 — narrative/handoff_note/
    patient_guidance만 수정 가능하다."""

    model_config = ConfigDict(from_attributes=True)

    patient: SnapshotPatient
    encounters: list[SnapshotEncounter]
    diagnoses: list[SnapshotDiagnosis]
    lab_results: list[SnapshotLabResult]
    lab_trends: list[SnapshotLabTrendGroup]
    prescriptions: list[SnapshotPrescription]
    allergies: list[SnapshotAllergy]
    safety_alerts: list[SnapshotSafetyAlert]
    clinical_notes: list[SnapshotClinicalNote]
    source_record_ids: list[str]


class ReportContentSnapshot(BaseModel):
    """ClinicalReport.content 컬럼에 저장되는 전체 구조.
    collect_report_data() -> EmrSnapshot.model_validate() -> 이 스키마로
    감싸서 model_dump(mode="json")한 결과가 그대로 저장된다. 조회 시에도
    저장된 dict를 다시 이 스키마로 검증한 뒤 응답한다."""

    emr_snapshot: EmrSnapshot
    narrative: str | None = None
    handoff_note: str | None = None
    patient_guidance: str | None = None


# --- 요청/응답 스키마 -----------------------------------------------------


class ClinicalReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_type: ClinicalReportType
    scope_type: ClinicalReportScopeType
    encounter_ids: list[int]

    @model_validator(mode="after")
    def _validate_task13_supported_combination(self) -> "ClinicalReportCreate":
        # 이번 Task는 DOCTOR_REFERENCE + SINGLE_ENCOUNTER만 지원한다.
        # 나머지 조합은 Enum에는 존재하지만 이 API에서는 422로 거부한다.
        if self.report_type != ClinicalReportType.DOCTOR_REFERENCE:
            raise ValueError("이번 버전에서는 report_type=DOCTOR_REFERENCE만 지원합니다.")
        if self.scope_type != ClinicalReportScopeType.SINGLE_ENCOUNTER:
            raise ValueError("이번 버전에서는 scope_type=SINGLE_ENCOUNTER만 지원합니다.")
        if len(self.encounter_ids) != 1:
            raise ValueError("encounter_ids는 정확히 1개여야 합니다.")
        return self


class ClinicalReportOut(BaseModel):
    id: int
    patient_id: int
    encounter_id: int | None
    report_type: str
    scope_type: str
    scope_encounter_ids: list[int]
    status: str
    content: ReportContentSnapshot
    created_by_user_id: int
    created_at: datetime
    last_modified_by_user_id: int
    last_modified_at: datetime
    reviewed_by_user_id: int | None
    reviewed_at: datetime | None
    supersedes_report_id: int | None
