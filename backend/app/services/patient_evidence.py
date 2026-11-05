"""승인된 환자용 보고서에 표시할 "근거 문구"를 만드는 서비스.

저장된 EmrSnapshot(및 그 안의 source_record_ids)만 사용한다 — 원본 EMR
테이블을 다시 조회하지 않는다. "record_type:id" 형식은
app/services/report_data.py의 _build_source_record_ids()가 이미 정한
결정적 순서를 그대로 따른다.

clinical_note와 safety_alert는 환자에게 노출하지 않기로 확정된 항목이라
(Task 19 정책) 애초에 근거 문구로 변환하지 않고 건너뛴다. 변환에 필요한
내부 레코드를 스냅샷 안에서 찾지 못하면(정상적으로는 일어나지 않아야
하는 상황) 그 항목도 조용히 건너뛴다 — 원본 ID를 그대로 노출하지
않는다.
"""

from __future__ import annotations

from datetime import date

from app.schemas.clinical_report import EmrSnapshot

_DEPARTMENT_LABELS = {
    "ENDOCRINOLOGY": "내분비내과",
    "ORTHOPEDICS": "정형외과",
    "EMERGENCY_MEDICINE": "응급의학과",
}

_EXCLUDED_RECORD_TYPES = {"clinical_note", "safety_alert"}


def _department_label(code: str) -> str:
    return _DEPARTMENT_LABELS.get(code, code)


def _korean_date(value: date) -> str:
    return f"{value.year}년 {value.month}월 {value.day}일"


def build_patient_evidence(snapshot: EmrSnapshot) -> list[str]:
    """source_record_ids를 사람이 이해할 수 있는 문장으로 변환한다.
    순서는 source_record_ids의 기존 결정적 순서를 그대로 따르고, 중복된
    문장은 처음 나온 자리만 남긴다."""
    encounters_by_id = {e.id: e for e in snapshot.encounters}
    diagnoses_by_id = {d.id: d for d in snapshot.diagnoses}
    lab_results_by_id = {lr.id: lr for lr in snapshot.lab_results}
    prescriptions_by_id = {p.id: p for p in snapshot.prescriptions}
    allergies_by_id = {a.id: a for a in snapshot.allergies}
    vital_signs_by_id = {v.id: v for v in snapshot.vital_signs}

    labels: list[str] = []
    for record_id in snapshot.source_record_ids:
        record_type, separator, raw_id = record_id.partition(":")
        if record_type in _EXCLUDED_RECORD_TYPES or not separator or not raw_id.isdigit():
            continue
        entity_id = int(raw_id)

        label: str | None = None
        if record_type == "encounter":
            encounter = encounters_by_id.get(entity_id)
            if encounter is not None:
                label = (
                    f"{_korean_date(encounter.start_time.date())} "
                    f"{_department_label(encounter.department)} 진료 방문"
                )
        elif record_type == "diagnosis":
            diagnosis = diagnoses_by_id.get(entity_id)
            encounter = encounters_by_id.get(diagnosis.encounter_id) if diagnosis else None
            if diagnosis is not None and encounter is not None:
                label = (
                    f"{_korean_date(encounter.start_time.date())} "
                    f"{_department_label(encounter.department)} 진단 기록"
                )
        elif record_type == "lab_result":
            lab_result = lab_results_by_id.get(entity_id)
            encounter = encounters_by_id.get(lab_result.encounter_id) if lab_result else None
            if lab_result is not None and encounter is not None:
                label = (
                    f"{_korean_date(encounter.start_time.date())} "
                    f"{_department_label(encounter.department)} {lab_result.test_name} 검사"
                )
        elif record_type == "prescription":
            prescription = prescriptions_by_id.get(entity_id)
            encounter = encounters_by_id.get(prescription.encounter_id) if prescription else None
            if prescription is not None and encounter is not None:
                label = (
                    f"{_korean_date(encounter.start_time.date())} "
                    f"{_department_label(encounter.department)} 처방 기록"
                )
        elif record_type == "allergy":
            allergy = allergies_by_id.get(entity_id)
            if allergy is not None:
                recorded_at = getattr(allergy, "recorded_at", None)
                label = (
                    f"{_korean_date(recorded_at.date())} 알레르기 기록"
                    if recorded_at is not None
                    else "등록된 알레르기 정보"
                )
        elif record_type == "vital_sign":
            # Task F4-B: vital_type/value처럼 세부 수치가 아니라 "측정이
            # 있었다"는 사실만 전달한다 - 같은 Encounter의 여러 VitalSign이
            # 전부 같은 날짜·진료과로 귀결되므로 아래 dedup으로 한 문장만
            # 남는다(의도된 동작 - 항목별로 7개씩 나열하지 않는다).
            vital = vital_signs_by_id.get(entity_id)
            encounter = encounters_by_id.get(vital.encounter_id) if vital else None
            if vital is not None and encounter is not None:
                label = (
                    f"{_korean_date(encounter.start_time.date())} "
                    f"{_department_label(encounter.department)} 활력징후 측정"
                )

        if label is not None and label not in labels:
            labels.append(label)

    return labels
