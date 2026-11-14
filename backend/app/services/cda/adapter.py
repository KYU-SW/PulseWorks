"""HL7-4A §7: CDA Input Adapter.

ReportContentSnapshot/report 메타데이터 -> CDA 전용 immutable 입력
DTO(CdaExportInput). 오직 projection만 한다 - DB 조회, AI 호출,
terminology/unit 변환, XML 지식을 전혀 갖지 않는다(HL7-2 §5). Mapper는
이 DTO만 보고 동작하며 ORM이나 Pydantic Snapshot 스키마에 직접
의존하지 않는다.

이 DTO에는 mentioned_vital_signs/mentioned_measurements/evidence_tags
같은 LLM self-report 필드가 존재하지 않는다 - Structured Entry는 이
필드들을 source로 쓰지 않는다는 원칙(HL7-0/HL7-2)을 타입 자체로
강제한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.schemas.clinical_report import (
    EmrSnapshot,
    SnapshotDiagnosis,
    SnapshotEncounter,
    SnapshotLabResult,
    SnapshotPatient,
    SnapshotVitalSign,
)


@dataclass(frozen=True)
class CdaExportInput:
    report_id: int
    report_type: str
    scope_type: str
    status: str
    created_by_user_id: int
    created_at: datetime
    reviewed_at: datetime | None
    narrative: str | None
    patient: SnapshotPatient
    encounter: SnapshotEncounter
    vital_signs: tuple[SnapshotVitalSign, ...]
    lab_results: tuple[SnapshotLabResult, ...]
    diagnoses: tuple[SnapshotDiagnosis, ...]


def build_cda_export_input(
    *,
    report_id: int,
    report_type: str,
    scope_type: str,
    status: str,
    created_by_user_id: int,
    created_at: datetime,
    reviewed_at: datetime | None,
    narrative: str | None,
    encounter_id: int,
    emr_snapshot: EmrSnapshot,
) -> CdaExportInput:
    """SINGLE_ENCOUNTER 보고서가 다루는 대표 Encounter를
    emr_snapshot에서 찾아(기존 patient_reports.py::_report_encounter()와
    동일한 불변조건 - collect_report_data()가 이미 이 Encounter를
    스냅샷에 포함시켰음을 전제한다) 그 Encounter에 속한 레코드만
    추린다."""
    encounter = next(e for e in emr_snapshot.encounters if e.id == encounter_id)

    return CdaExportInput(
        report_id=report_id,
        report_type=report_type,
        scope_type=scope_type,
        status=status,
        created_by_user_id=created_by_user_id,
        created_at=created_at,
        reviewed_at=reviewed_at,
        narrative=narrative,
        patient=emr_snapshot.patient,
        encounter=encounter,
        vital_signs=tuple(v for v in emr_snapshot.vital_signs if v.encounter_id == encounter_id),
        lab_results=tuple(l for l in emr_snapshot.lab_results if l.encounter_id == encounter_id),
        diagnoses=tuple(d for d in emr_snapshot.diagnoses if d.encounter_id == encounter_id),
    )
