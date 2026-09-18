"""보고서 생성을 위한 읽기 전용 자료 수집 서비스.

이 모듈은 기존 EMR 데이터베이스를 조회만 한다 — DB 레코드를 추가·수정·
삭제하지 않고, db.commit()/db.flush()를 호출하지 않고, 감사 로그를
남기지 않고, HTTPException을 직접 만들지 않는다. DB를 조회하므로
services/safety_rules.py의 함수들과 달리 순수 함수는 아니지만, 그 외의
모든 부작용(side effect)이 없다는 점은 동일하게 보장한다.

Mock AI 설명문(narrative), AiSummary, ClinicalReport 상태/생성자/승인자
같은 보고서 자체의 메타데이터는 이 Task의 책임이 아니다 — 이 서비스는
"보고서에 넣을 원재료"만 모으고, 그 재료로 무엇을 만들지는 이후 Task
(13 이후)의 몫이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models import (
    Allergy,
    ClinicalNote,
    Diagnosis,
    Encounter,
    LabResult,
    Patient,
    Prescription,
    SafetyAlert,
)
from app.services.lab_trend_grouping import LabTrendGroup, group_lab_results_by_test
from app.services.safety_rules import evaluate_lab_abnormal
from app.utils.text import truncate_for_display

# source_record_ids를 결정적인 순서로 만들기 위한 고정된 레코드 종류 순서.
_SOURCE_RECORD_TYPE_ORDER = (
    "encounter",
    "diagnosis",
    "lab_result",
    "prescription",
    "allergy",
    "safety_alert",
    "clinical_note",
)


class ReportScopeError(Exception):
    """encounter_ids가 비었거나, 존재하지 않거나, 다른 환자에 속하는 경우.

    이 예외는 HTTPException이 아니다 — 이 서비스는 HTTP를 모른다. Task 13
    라우터가 이 예외를 일반화된 404로 변환하는 책임을 진다(어떤 원인인지
    구분해 노출하지 않는다: 존재하지 않음과 다른 환자 소속을 구분하면
    Task 8/10과 동일한 이유로 정보가 새어나간다)."""


@dataclass(frozen=True)
class ReportPatient:
    id: int
    mrn: str
    name: str
    birth_date: date


@dataclass(frozen=True)
class ReportEncounter:
    id: int
    department: str
    encounter_type: str
    start_time: datetime
    end_time: datetime | None


@dataclass(frozen=True)
class ReportDiagnosis:
    id: int
    encounter_id: int
    code: str
    description: str
    diagnosed_at: datetime
    source_type: str


@dataclass(frozen=True)
class ReportLabResult:
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


@dataclass(frozen=True)
class ReportPrescription:
    id: int
    encounter_id: int
    medication_name: str
    dosage: str
    prescribed_by_user_id: int
    prescribed_at: datetime
    source_type: str


@dataclass(frozen=True)
class ReportAllergy:
    id: int
    substance: str
    reaction: str
    severity: str
    recorded_at: datetime
    source_type: str


@dataclass(frozen=True)
class ReportSafetyAlert:
    id: int
    encounter_id: int
    prescription_id: int | None
    lab_result_id: int | None
    rule_id: str
    priority: str
    evidence: dict
    created_at: datetime


@dataclass(frozen=True)
class ReportClinicalNote:
    id: int
    encounter_id: int
    author_user_id: int
    preview_text: str
    created_at: datetime
    source_type: str


@dataclass(frozen=True)
class ReportData:
    """보고서 생성에 필요한 원재료 묶음. narrative/AiSummary/ClinicalReport
    상태·생성자·승인자·환자용 쉬운 표현·진료과별 템플릿 정보는 이 Task의
    책임이 아니므로 여기에 없다."""

    patient: ReportPatient
    encounters: list[ReportEncounter]
    diagnoses: list[ReportDiagnosis]
    lab_results: list[ReportLabResult]
    lab_trends: list[LabTrendGroup]
    prescriptions: list[ReportPrescription]
    allergies: list[ReportAllergy]
    safety_alerts: list[ReportSafetyAlert]
    clinical_notes: list[ReportClinicalNote]
    source_record_ids: list[str] = field(default_factory=list)


def _build_source_record_ids(
    encounters: list[Encounter],
    diagnoses: list[Diagnosis],
    lab_results_raw: list,
    prescriptions: list[Prescription],
    allergies: list[Allergy],
    safety_alerts: list[SafetyAlert],
    clinical_notes: list[ClinicalNote],
) -> list[str]:
    ids_by_type: dict[str, list[int]] = {
        "encounter": [e.id for e in encounters],
        "diagnosis": [d.id for d in diagnoses],
        "lab_result": [lr.id for lr in lab_results_raw],
        "prescription": [p.id for p in prescriptions],
        "allergy": [a.id for a in allergies],
        "safety_alert": [s.id for s in safety_alerts],
        "clinical_note": [n.id for n in clinical_notes],
    }
    record_ids: list[str] = []
    for record_type in _SOURCE_RECORD_TYPE_ORDER:
        for record_id in sorted(set(ids_by_type[record_type])):
            record_ids.append(f"{record_type}:{record_id}")
    return record_ids


def _to_report_lab_result(lab_result: LabResult) -> ReportLabResult:
    judgment = evaluate_lab_abnormal(
        lab_result.value, lab_result.reference_low, lab_result.reference_high, lab_result.unit
    )
    return ReportLabResult(
        id=lab_result.id,
        encounter_id=lab_result.encounter_id,
        test_name=lab_result.test_name,
        value=lab_result.value,
        unit=lab_result.unit,
        reference_low=lab_result.reference_low,
        reference_high=lab_result.reference_high,
        measured_at=lab_result.measured_at,
        source_type=lab_result.source_type.value,
        status=judgment.status.value,
        rule_id=judgment.rule_id,
    )


def collect_report_data(
    db: Session,
    patient_id: int,
    encounter_ids: list[int],
) -> ReportData:
    """선택된 encounter_ids(+환자 레벨 Allergy)로 보고서 원재료를 모은다.

    encounter_ids가 비어 있거나, 그중 하나라도 존재하지 않거나 다른
    환자에게 속하면 ReportScopeError를 일으키고 아무 데이터도 반환하지
    않는다 — 유효한 Encounter만 골라 부분 보고서를 만들지 않는다.
    """
    if not encounter_ids:
        raise ReportScopeError("encounter_ids must not be empty")

    unique_encounter_ids = list(dict.fromkeys(encounter_ids))
    encounters = (
        db.query(Encounter).filter(Encounter.id.in_(unique_encounter_ids)).all()
    )
    found_ids = {e.id for e in encounters}
    if found_ids != set(unique_encounter_ids):
        raise ReportScopeError("one or more encounter_ids do not exist")
    if any(e.patient_id != patient_id for e in encounters):
        raise ReportScopeError("one or more encounter_ids belong to a different patient")

    # 위 검사를 통과했다는 것은 모든 encounter_ids가 실제로 patient_id에
    # 속한다는 뜻이고, Encounter.patient_id는 ON DELETE RESTRICT로 Patient를
    # 참조하므로 patient는 반드시 존재한다.
    patient = db.query(Patient).filter_by(id=patient_id).first()

    diagnoses = (
        db.query(Diagnosis).filter(Diagnosis.encounter_id.in_(unique_encounter_ids)).all()
    )
    lab_results_raw = (
        db.query(LabResult).filter(LabResult.encounter_id.in_(unique_encounter_ids)).all()
    )
    prescriptions = (
        db.query(Prescription).filter(Prescription.encounter_id.in_(unique_encounter_ids)).all()
    )
    clinical_notes = (
        db.query(ClinicalNote).filter(ClinicalNote.encounter_id.in_(unique_encounter_ids)).all()
    )
    safety_alerts = (
        db.query(SafetyAlert).filter(SafetyAlert.encounter_id.in_(unique_encounter_ids)).all()
    )
    allergies = db.query(Allergy).filter_by(patient_id=patient_id).all()

    lab_trends = group_lab_results_by_test(lab_results_raw)

    source_record_ids = _build_source_record_ids(
        encounters=encounters,
        diagnoses=diagnoses,
        lab_results_raw=lab_results_raw,
        prescriptions=prescriptions,
        allergies=allergies,
        safety_alerts=safety_alerts,
        clinical_notes=clinical_notes,
    )

    return ReportData(
        patient=ReportPatient(
            id=patient.id,
            mrn=patient.mrn,
            name=patient.full_name,
            birth_date=patient.birth_date,
        ),
        encounters=[
            ReportEncounter(
                id=e.id,
                department=e.department.value,
                encounter_type=e.encounter_type.value,
                start_time=e.start_time,
                end_time=e.end_time,
            )
            for e in encounters
        ],
        diagnoses=[
            ReportDiagnosis(
                id=d.id,
                encounter_id=d.encounter_id,
                code=d.code,
                description=d.description,
                diagnosed_at=d.diagnosed_at,
                source_type=d.source_type.value,
            )
            for d in diagnoses
        ],
        lab_results=[_to_report_lab_result(lr) for lr in lab_results_raw],
        lab_trends=lab_trends,
        prescriptions=[
            ReportPrescription(
                id=p.id,
                encounter_id=p.encounter_id,
                medication_name=p.medication_name,
                dosage=p.dosage,
                prescribed_by_user_id=p.prescribed_by_user_id,
                prescribed_at=p.prescribed_at,
                source_type=p.source_type.value,
            )
            for p in prescriptions
        ],
        allergies=[
            ReportAllergy(
                id=a.id,
                substance=a.substance,
                reaction=a.reaction,
                severity=a.severity,
                recorded_at=a.recorded_at,
                source_type=a.source_type.value,
            )
            for a in allergies
        ],
        safety_alerts=[
            ReportSafetyAlert(
                id=s.id,
                encounter_id=s.encounter_id,
                prescription_id=s.prescription_id,
                lab_result_id=s.lab_result_id,
                rule_id=s.rule_id,
                priority=s.priority.value,
                evidence=s.evidence,
                created_at=s.created_at,
            )
            for s in safety_alerts
        ],
        clinical_notes=[
            ReportClinicalNote(
                id=n.id,
                encounter_id=n.encounter_id,
                author_user_id=n.author_user_id,
                preview_text=truncate_for_display(n.note_text),
                created_at=n.created_at,
                source_type=n.source_type.value,
            )
            for n in clinical_notes
        ],
        source_record_ids=source_record_ids,
    )
