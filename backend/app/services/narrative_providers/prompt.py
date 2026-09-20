"""RealLLMProvider가 외부 LLM에 보낼 프롬프트를 조립한다.

Task 19 설계 확정사항(최소 입력 데이터)을 그대로 따른다 - 환자 이름,
MRN, 생년월일, 사용자 ID, ClinicalNote, SafetyAlert는 절대 포함하지
않는다. 순수 함수이며 스냅샷을 수정하지 않는다.
"""

from app.schemas.clinical_report import EmrSnapshot

_INSTRUCTIONS = (
    "다음은 진료 기록 요약 자료다. 이 자료에 있는 사실만 근거로 삼아 "
    "한국어 설명문(narrative)을 작성하라.\n"
    "narrative에서 언급한 모든 검사 수치는 반드시 mentioned_measurements에도 "
    "포함하라.\n"
    "narrative를 작성하는 데 사용한 모든 근거는 cited_record_ids에 포함하라.\n"
    "이 자료에 없는 새로운 수치나 근거를 만들지 마라.\n"
    "다음을 포함하지 마라: 새로운 진단 확정, 질환 악화·호전 확정, 치료 권고, "
    "약물 추가·변경·중단 지시, 재검사 지시, 위험도 확정, 예후 예측."
)


def build_narrative_prompt(snapshot: EmrSnapshot) -> str:
    lines = [_INSTRUCTIONS, ""]

    lines.append("[진료 방문]")
    for encounter in snapshot.encounters:
        lines.append(f"- {encounter.department} {encounter.encounter_type} {encounter.start_time}")

    lines.append("[진단]")
    for diagnosis in snapshot.diagnoses:
        lines.append(f"- {diagnosis.description} ({diagnosis.diagnosed_at})")

    lines.append("[검사결과]")
    for lab in snapshot.lab_results:
        lines.append(
            f"- {lab.test_name}: {lab.value}{lab.unit} "
            f"(참고범위 {lab.reference_low}-{lab.reference_high}{lab.unit}, "
            f"측정 {lab.measured_at}, 판정 {lab.status})"
        )

    lines.append("[처방]")
    for prescription in snapshot.prescriptions:
        lines.append(f"- {prescription.medication_name} {prescription.dosage}")

    lines.append("[알레르기]")
    for allergy in snapshot.allergies:
        lines.append(f"- {allergy.substance}: {allergy.reaction} ({allergy.severity})")

    lines.append("[근거 ID 목록]")
    lines.append(", ".join(snapshot.source_record_ids))

    return "\n".join(lines)
