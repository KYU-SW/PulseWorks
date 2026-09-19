from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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


class ClinicalReportPatch(BaseModel):
    """DRAFT(또는 REJECTED — 자동으로 DRAFT로 전환됨) 보고서의 서술형
    필드만 수정하는 요청. emr_snapshot/patient_id/status 등은 이 스키마에
    필드 자체가 없으므로 extra="forbid"가 자동으로 422 거부한다.

    exclude_unset=True로 model_dump()해야 "전달 안 함"과 "명시적으로
    null 전달"을 구분할 수 있다 — 라우터가 이 구분을 사용한다."""

    model_config = ConfigDict(extra="forbid")

    narrative: str | None = Field(default=None, max_length=10000)
    handoff_note: str | None = Field(default=None, max_length=10000)
    patient_guidance: str | None = Field(default=None, max_length=10000)

    @field_validator("narrative", "handoff_note", "patient_guidance")
    @classmethod
    def _blank_string_becomes_none(cls, value: str | None) -> str | None:
        if value is not None and value.strip() == "":
            return None
        return value

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "ClinicalReportPatch":
        if not self.model_fields_set:
            raise ValueError(
                "narrative, handoff_note, patient_guidance 중 최소 하나는 포함해야 합니다."
            )
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
