from datetime import date, datetime
from decimal import Decimal

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


class SnapshotVitalSign(BaseModel):
    """Task F4-B: 보고서 생성 시점의 VitalSign 동결. 품질 경고·BMI는
    여기 없다 - 조회 시점에 다시 계산하는 파생값이라 Snapshot에 넣지
    않는다(app/services/report_data.py의 ReportVitalSign과 1:1 대응)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    encounter_id: int
    vital_type: str
    value: Decimal
    value_secondary: Decimal | None
    unit: str
    measured_at: datetime


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
    # Task F4-B: 선택적 필드(기본값 [])라 Migration이 필요 없다 - 이
    # 필드가 없는 기존 JSON도 기본값으로 그대로 파싱된다(Task D1의
    # narrative_source/narrative_edited_by_clinician과 같은 원칙).
    vital_signs: list[SnapshotVitalSign] = Field(default_factory=list)
    source_record_ids: list[str]


class ReportContentSnapshot(BaseModel):
    """ClinicalReport.content 컬럼에 저장되는 전체 구조.
    collect_report_data() -> EmrSnapshot.model_validate() -> 이 스키마로
    감싸서 model_dump(mode="json")한 결과가 그대로 저장된다. 조회 시에도
    저장된 dict를 다시 이 스키마로 검증한 뒤 응답한다.

    Task D1(narrative 출처 표시): narrative_source/narrative_edited_by_clinician은
    선택적 필드라 Migration이 필요 없다 - 이 필드가 없는 기존 JSON도
    기본값(None/False)으로 그대로 파싱된다. 의사용 ClinicalReportOut.content가
    이 스키마를 그대로 쓰므로 의사 화면에는 자동으로 노출되지만,
    환자용 스키마(app/schemas/patient_report.py)는 필드를 하나하나
    별도로 나열하는 완전히 다른 클래스라 이 필드들을 추가하지 않는 한
    환자 API에는 절대 새지 않는다."""

    emr_snapshot: EmrSnapshot
    narrative: str | None = None
    handoff_note: str | None = None
    patient_guidance: str | None = None
    # "mock"(DeterministicMockProvider) | "llm"(RealLLMProvider, 벤더 무관) |
    # "clinician"(비어 있던 narrative를 의료진이 처음 작성) | None(기존
    # 보고서처럼 최초 출처를 정확히 알 수 없음 - 감사 로그를 역추적해
    # 추측하지 않는다).
    narrative_source: str | None = None
    # 최초 생성 이후 의료진이 narrative 내용을 실제로 바꾼 적이 있는지.
    # narrative_source와 별개로 관리한다 - "AI가 초안을 만들었다"는
    # 사실과 "의료진이 그 초안을 수정했다"는 사실을 둘 다 표현하기 위함.
    narrative_edited_by_clinician: bool = False


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
