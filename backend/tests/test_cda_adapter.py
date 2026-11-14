"""HL7-4A §7: CDA Input Adapter 테스트.

Adapter는 ReportContentSnapshot/report 메타데이터에서 CDA 전용 immutable
DTO를 만드는 순수 projection 함수다 - DB 조회, AI 호출, terminology/unit
변환을 하지 않는다(그 책임은 mapper.py/terminology.py).
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from app.schemas.clinical_report import (
    EmrSnapshot,
    SnapshotDiagnosis,
    SnapshotEncounter,
    SnapshotLabResult,
    SnapshotPatient,
    SnapshotVitalSign,
)
from app.services.cda.adapter import build_cda_export_input

_PATIENT = SnapshotPatient(id=1, mrn="SYN-0001", name="김합성", birth_date=date(1990, 1, 1))
_ENCOUNTER = SnapshotEncounter(
    id=10,
    department="ENDOCRINOLOGY",
    encounter_type="OUTPATIENT",
    start_time=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
    end_time=None,
)
_OTHER_ENCOUNTER = SnapshotEncounter(
    id=11,
    department="ORTHOPEDICS",
    encounter_type="OUTPATIENT",
    start_time=datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc),
    end_time=None,
)


def _snapshot(**overrides) -> EmrSnapshot:
    base = dict(
        patient=_PATIENT,
        encounters=[_ENCOUNTER, _OTHER_ENCOUNTER],
        diagnoses=[
            SnapshotDiagnosis(
                id=100,
                encounter_id=10,
                code="E11.9",
                description="2형 당뇨병",
                diagnosed_at=datetime(2026, 3, 10, 9, 10, tzinfo=timezone.utc),
                source_type="DOCTOR",
            ),
            SnapshotDiagnosis(
                id=101,
                encounter_id=11,
                code="M17.9",
                description="무관한 진단",
                diagnosed_at=datetime(2026, 1, 1, 9, 10, tzinfo=timezone.utc),
                source_type="DOCTOR",
            ),
        ],
        lab_results=[
            SnapshotLabResult(
                id=200,
                encounter_id=10,
                test_name="HbA1c",
                value=7.2,
                unit="%",
                reference_low=4.0,
                reference_high=6.0,
                measured_at=datetime(2026, 3, 10, 9, 5, tzinfo=timezone.utc),
                source_type="DOCTOR",
                status="HIGH",
                rule_id="r1",
            )
        ],
        lab_trends=[],
        prescriptions=[],
        allergies=[],
        safety_alerts=[],
        clinical_notes=[],
        vital_signs=[
            SnapshotVitalSign(
                id=300,
                encounter_id=10,
                vital_type="BODY_TEMPERATURE",
                value=Decimal("36.5"),
                value_secondary=None,
                unit="Cel",
                measured_at=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
            )
        ],
        source_record_ids=["diagnosis:100", "lab_result:200", "vital_sign:300"],
    )
    base.update(overrides)
    return EmrSnapshot.model_validate(base)


class TestBuildCdaExportInput:
    def test_projects_report_metadata(self):
        result = build_cda_export_input(
            report_id=1,
            report_type="DOCTOR_REFERENCE",
            scope_type="SINGLE_ENCOUNTER",
            status="APPROVED",
            created_by_user_id=5,
            created_at=datetime(2026, 3, 10, 9, 30, tzinfo=timezone.utc),
            reviewed_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
            narrative="환자는 2형 당뇨병이 신규로 진단되었습니다.",
            encounter_id=10,
            emr_snapshot=_snapshot(),
        )
        assert result.report_id == 1
        assert result.reviewed_at == datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc)
        assert result.patient.mrn == "SYN-0001"
        assert result.encounter.id == 10

    def test_filters_diagnoses_to_target_encounter_only(self):
        result = build_cda_export_input(
            report_id=1,
            report_type="DOCTOR_REFERENCE",
            scope_type="SINGLE_ENCOUNTER",
            status="APPROVED",
            created_by_user_id=5,
            created_at=datetime(2026, 3, 10, 9, 30, tzinfo=timezone.utc),
            reviewed_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
            narrative="narrative",
            encounter_id=10,
            emr_snapshot=_snapshot(),
        )
        assert [d.id for d in result.diagnoses] == [100]
        assert [v.id for v in result.vital_signs] == [300]
        assert [l.id for l in result.lab_results] == [200]

    def test_does_not_use_llm_self_report_fields(self):
        # Adapter의 반환 타입에는 mentioned_vital_signs/mentioned_measurements/
        # evidence_tags 같은 LLM self-report 필드가 존재하지 않는다 -
        # dataclass 필드 자체로 구조적으로 강제된다.
        import dataclasses

        result = build_cda_export_input(
            report_id=1,
            report_type="DOCTOR_REFERENCE",
            scope_type="SINGLE_ENCOUNTER",
            status="APPROVED",
            created_by_user_id=5,
            created_at=datetime(2026, 3, 10, 9, 30, tzinfo=timezone.utc),
            reviewed_at=datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc),
            narrative="narrative",
            encounter_id=10,
            emr_snapshot=_snapshot(),
        )
        field_names = {f.name for f in dataclasses.fields(result)}
        assert "mentioned_vital_signs" not in field_names
        assert "evidence_tags" not in field_names
