"""RealLLMProvider가 외부 LLM에 보낼 프롬프트를 조립한다.

Task 19 설계 확정사항(최소 입력 데이터)을 그대로 따른다 - 환자 이름,
MRN, 생년월일, 사용자 ID, ClinicalNote, SafetyAlert는 절대 포함하지
않는다. 순수 함수이며 스냅샷을 수정하지 않는다.

Task A(익명 근거 태그) 확정사항: 실제 source_record_ids(내부 숫자 PK가
담긴 "type:id" 문자열)와 내부 숫자 PK는 프롬프트에 절대 포함하지 않는다.
대신 각 항목에 이 요청 한정으로만 의미 있는 익명 태그(E=Encounter,
D=Diagnosis, L=LabResult, P=Prescription, A=Allergy + 그 종류 안에서의
등장 순번)를 붙이고, "태그 -> 실제 source_record_id" 매핑은
NarrativePrompt.tag_to_source_record_id로 서버 내부에만 보존한다 -
RealLLMProvider가 LLM이 돌려준 태그를 이 매핑으로 역매핑한다.

evidence_tags 후속 검증 원인 분석(2026-09-30 실제 Ollama 수동 검증)
확정사항: evidence_tags 관련 지시는 맨 위 _INSTRUCTIONS가 아니라 모든
임상 데이터 섹션 뒤, 출력 직전의 마무리 블록에 둔다 - 실제 사용 가능한
태그 전체 목록([사용 가능한 태그] ...)도 그 블록에서 한 번에 보여준다.
_INSTRUCTIONS에는 태그와 무관한 일반 규칙만 남긴다(최신성 효과로
모델이 태그 규칙을 출력 직전에 다시 읽게 하기 위함 - evidence_tags가
빈 배열로 돌아온 실제 관찰에 대한 최소 대응책 중 하나).

Task C1(2026-09-30 실제 Ollama 수동 검증에서 narrative 본문에 "(E1)",
"(D1)" 노출 발견) 확정사항: 태그를 narrative 본문에 쓰지 말라는 금지를
_EVIDENCE_TAGS_REMINDER에 함께 명시한다(같은 자리, 중복 배치 없음) -
서버 쪽 방어는 app/services/narrative_validation.py가 맡는다(이 파일은
프롬프트로 빈도를 낮추는 역할만).

Department/EncounterType 한글 라벨은 app/services/mock_narrative.py의
동일 매핑을 그대로 재사용한 값이지만, 그 파일의 private 상수를 다른
서비스가 import하지 않는다는 원칙 때문에 이 파일에 독립적으로 다시
선언한다(같은 값, Enum 키 기준으로 직접 확인) - 영문 Enum 원문을 그대로
LLM에 보내면 모델이 "내분비학"처럼 임의로 다시 번역해 앱 전체가 쓰는
표준 용어("내분비내과")와 어긋나는 문제의 최소 대응."""

from dataclasses import dataclass, field

from app.schemas.clinical_report import EmrSnapshot

# app/services/mock_narrative.py 및 프론트엔드 여러 화면과 동일한 값 -
# 이 파일 밖으로 옮기는 공통화는 mock_narrative.py를 건드려야 해서
# 이번 Task C1 범위 밖이다(허용 파일 목록 참고). 알 수 없는 값은 원문을
# 그대로 쓴다(.get() 기본값) - 임의로 새 라벨을 추측해 넣지 않는다.
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

_INSTRUCTIONS = (
    "다음은 진료 기록 요약 자료다. 이 자료에 있는 사실만 근거로 삼아 "
    "한국어 설명문(narrative)을 작성하라.\n"
    "narrative에서 언급한 모든 검사 수치는 반드시 mentioned_measurements에도 "
    "포함하라.\n"
    "이 자료에 없는 새로운 수치나 근거를 만들지 마라.\n"
    "다음을 포함하지 마라: 새로운 진단 확정, 질환 악화·호전 확정, 치료 권고, "
    "약물 추가·변경·중단 지시, 재검사 지시, 위험도 확정, 예후 예측."
)

_EVIDENCE_TAGS_REMINDER = (
    "narrative를 작성하는 데 실제로 사용한 위 태그만 evidence_tags에 "
    "최소 1개 이상 포함하라. 목록에 없는 태그를 만들지 마라.\n"
    "evidence_tags는 JSON의 evidence_tags 필드에만 넣는다. narrative는 "
    "환자가 읽는 자연어 설명문이다 - narrative 본문에는 E1, D1, L1, P1, "
    "A1 같은 태그를 [ ], ( ), { }로 감싸 쓰거나 \"근거 E1\", \"출처 D1\" "
    "처럼 인용하지 마라. 태그는 애플리케이션 내부 근거 연결에만 쓰인다."
)


@dataclass(frozen=True)
class NarrativePrompt:
    text: str
    # 이 호출 한정 익명 태그 -> 실제 snapshot.source_record_ids 문자열.
    # 프롬프트 text 안에는 이 매핑의 값(실제 ID)이 등장하지 않는다.
    tag_to_source_record_id: dict[str, str] = field(default_factory=dict)


def build_narrative_prompt(snapshot: EmrSnapshot) -> NarrativePrompt:
    tag_map: dict[str, str] = {}
    lines = [_INSTRUCTIONS, ""]

    lines.append("[진료 방문]")
    for index, encounter in enumerate(snapshot.encounters, start=1):
        tag = f"E{index}"
        tag_map[tag] = f"encounter:{encounter.id}"
        department = _DEPARTMENT_LABELS.get(encounter.department, encounter.department)
        encounter_type = _ENCOUNTER_TYPE_LABELS.get(encounter.encounter_type, encounter.encounter_type)
        lines.append(f"- [{tag}] {department} {encounter_type} {encounter.start_time}")

    lines.append("[진단]")
    for index, diagnosis in enumerate(snapshot.diagnoses, start=1):
        tag = f"D{index}"
        tag_map[tag] = f"diagnosis:{diagnosis.id}"
        lines.append(f"- [{tag}] {diagnosis.description} ({diagnosis.diagnosed_at})")

    lines.append("[검사결과]")
    for index, lab in enumerate(snapshot.lab_results, start=1):
        tag = f"L{index}"
        tag_map[tag] = f"lab_result:{lab.id}"
        lines.append(
            f"- [{tag}] {lab.test_name}: {lab.value}{lab.unit} "
            f"(참고범위 {lab.reference_low}-{lab.reference_high}{lab.unit}, "
            f"측정 {lab.measured_at}, 판정 {lab.status})"
        )

    lines.append("[처방]")
    for index, prescription in enumerate(snapshot.prescriptions, start=1):
        tag = f"P{index}"
        tag_map[tag] = f"prescription:{prescription.id}"
        lines.append(f"- [{tag}] {prescription.medication_name} {prescription.dosage}")

    lines.append("[알레르기]")
    for index, allergy in enumerate(snapshot.allergies, start=1):
        tag = f"A{index}"
        tag_map[tag] = f"allergy:{allergy.id}"
        lines.append(f"- [{tag}] {allergy.substance}: {allergy.reaction} ({allergy.severity})")

    # 데이터 유형이 없으면(예: 진단 0건) 그 유형의 태그는 tag_map에도,
    # 아래 [사용 가능한 태그] 목록에도 등장하지 않는다 - 위 루프들이
    # 존재하는 항목에만 태그를 부여하기 때문에 자동으로 지켜진다.
    lines.append("")
    lines.append(f"[사용 가능한 태그] {', '.join(tag_map.keys())}")
    lines.append(_EVIDENCE_TAGS_REMINDER)

    return NarrativePrompt(text="\n".join(lines), tag_to_source_record_id=tag_map)
