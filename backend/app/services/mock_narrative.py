"""ClinicalReport.content.narrative를 채우는 결정적 Mock 설명문 생성기.

DB/HTTP에 의존하지 않는 순수 함수다 — app.schemas.clinical_report.EmrSnapshot
(저장된 스냅샷을 재검증한 결과)만 입력받고, 같은 스냅샷에는 항상 같은
문자열을 반환한다. 실제 LLM이나 외부 AI API를 호출하지 않으며, 난수나
현재 시각에 의존하지 않는다.

이미 기록된 사실(진단명, 검사값·판정, 처방명, 알레르기, SafetyAlert,
진료기록 미리보기)을 고정된 한국어 문장 틀에 기계적으로 끼워 넣을
뿐이다 — 새 진단, 악화/호전 확정, 치료·처방 변경 권고, 재검사 지시,
위험도 확정, 예후 예측을 만들지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.clinical_report import EmrSnapshot

_PROVIDER = "DETERMINISTIC_MOCK"
_VERSION = "1"

_DISCLAIMER = (
    "이 설명은 합성 임상기록을 정해진 규칙으로 정리한 초안이며, "
    "의료진의 검토가 필요합니다."
)

_DEPARTMENT_LABELS = {
    "ENDOCRINOLOGY": "내분비내과",
    "ORTHOPEDICS": "정형외과",
    "EMERGENCY_MEDICINE": "응급의학과",
}
_ENCOUNTER_TYPE_LABELS = {
    "OUTPATIENT": "외래",
    "INPATIENT": "입원",
    "EMERGENCY": "응급",
}
_LAB_STATUS_LABELS = {
    "LOW": "낮음",
    "NORMAL": "정상",
    "HIGH": "높음",
    "UNKNOWN": "판정불가",
}
_PRIORITY_LABELS = {
    "HIGH": "높음",
    "MEDIUM": "중간",
    "LOW": "낮음",
}


@dataclass(frozen=True)
class MockNarrativeResult:
    summary_text: str
    source_record_ids: list[str]
    provider: str
    version: str


def generate_mock_report_narrative(snapshot: EmrSnapshot) -> MockNarrativeResult:
    """저장된 스냅샷만으로 설명문을 조립한다. 구성 순서는 Encounter →
    Diagnosis → LabResult → Prescription → Allergy → SafetyAlert →
    ClinicalNote로 고정되어 있다(source_record_ids의 타입 순서와 동일) —
    같은 스냅샷이면 항상 같은 문자열이 나온다."""
    lines: list[str] = []

    for encounter in snapshot.encounters:
        department = _DEPARTMENT_LABELS.get(encounter.department, encounter.department)
        encounter_type = _ENCOUNTER_TYPE_LABELS.get(
            encounter.encounter_type, encounter.encounter_type
        )
        lines.append(f"{department} {encounter_type} 방문 기록이 있습니다 (Encounter #{encounter.id}).")

    for diagnosis in snapshot.diagnoses:
        lines.append(f"등록된 진단: {diagnosis.description} ({diagnosis.code}).")

    for lab in snapshot.lab_results:
        status_label = _LAB_STATUS_LABELS.get(lab.status, lab.status)
        lines.append(
            f"{lab.test_name} 결과 {lab.value}{lab.unit} "
            f"(참고범위 {lab.reference_low}-{lab.reference_high}{lab.unit}, 판정: {status_label})."
        )

    for prescription in snapshot.prescriptions:
        lines.append(f"처방 기록: {prescription.medication_name} {prescription.dosage}.")

    for allergy in snapshot.allergies:
        lines.append(f"등록된 알레르기: {allergy.substance} ({allergy.reaction}).")

    for alert in snapshot.safety_alerts:
        priority_label = _PRIORITY_LABELS.get(alert.priority, alert.priority)
        lines.append(f"안전 알림 기록: {alert.rule_id} (우선순위 {priority_label}).")

    for note in snapshot.clinical_notes:
        lines.append(f"진료기록 미리보기: {note.preview_text}")

    if not lines:
        lines.append("이 범위에 표시할 기록이 없습니다.")

    lines.append(_DISCLAIMER)

    return MockNarrativeResult(
        summary_text=" ".join(lines),
        source_record_ids=list(snapshot.source_record_ids),
        provider=_PROVIDER,
        version=_VERSION,
    )
