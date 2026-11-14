"""HL7-4A: CDA Intermediate Representation(IR)의 최소 타입 집합.

HL7-2 §7/§9의 설계를 그대로 구현한다 - 전체 CDA 메타모델을 재구현하지
않고, 이 프로젝트가 실제로 쓰는 범위(Header 일부 + 4개 MVP Section)만
다룬다. 모든 타입은 immutable(frozen dataclass)이며, XML 태그 이름이나
네임스페이스 문자열을 전혀 알지 못한다 - 그 지식은 exporter.py에만
있다(HL7-2 §7 "책임 분리" 원칙).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

# HL7-1A에서 확인한 공식 uid 포맷 중 이 프로젝트가 채택한 UUID 표기 -
# 하이픈 포함 8-4-4-4-12, urn:uuid: 접두사 없음. HL7-3 §5 결정에 따라
# UUID version(니블)은 제한하지 않는다 - CDA schema 자체가 버전을
# 검사하지 않으므로, 애플리케이션이 추가 제약을 발명하지 않는다.
_UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def validate_uuid_root(value: str, field_name: str = "root") -> None:
    """II.root(또는 그 root로 쓰일 config 값)가 HL7-3A에서 확정한 형식을
    지키는지 확인한다. Identifier와 CDA Settings 검증(HL7-4A §5)이 같은
    규칙을 공유하도록 이 함수 하나로 모은다."""
    if value == "":
        raise ValueError(f"{field_name}은 비어 있을 수 없습니다.")
    if value != value.strip():
        raise ValueError(f"{field_name}에 앞뒤 whitespace를 포함할 수 없습니다: {value!r}")
    if value.startswith("urn:uuid:"):
        raise ValueError(
            f"{field_name}에는 urn:uuid: 접두사를 포함하지 않습니다(HL7-1A §17): {value!r}"
        )
    if not _UUID_PATTERN.match(value):
        raise ValueError(f"{field_name}은 UUID 형식(8-4-4-4-12)이어야 합니다: {value!r}")


@dataclass(frozen=True)
class Identifier:
    """CDA II(Instance Identifier) 표현. root는 identifier namespace,
    extension은 그 namespace 안의 로컬 식별자다(HL7-2 §10/HL7-3 §6).
    extension이 None이면 "이 namespace 자체가 곧 식별자"라는 뜻이고,
    빈 문자열("")은 "없음"과 모호하게 섞이므로 금지한다."""

    root: str
    extension: str | None = None

    def __post_init__(self) -> None:
        validate_uuid_root(self.root, field_name="root")
        if self.extension == "":
            raise ValueError("extension은 None 또는 비어있지 않은 문자열이어야 합니다(빈 문자열 금지).")


_TerminologyState = Literal["known", "unknown", "raw_unverified"]


@dataclass(frozen=True)
class CodedValue:
    """CD/CE 표현. HL7-2 §9/§11에서 설계한 3-state 모델을 구현한다 -
    세 상태를 하나의 모호한 구조로 합치지 않고, 생성자를 분리해 잘못된
    조합(예: unknown인데 code가 있음)을 구조적으로 막는다."""

    state: _TerminologyState
    code: str | None = None
    code_system: str | None = None
    display_name: str | None = None
    null_flavor: str | None = None
    raw_code: str | None = None
    original_text: str | None = None

    @classmethod
    def known(cls, *, code: str, code_system: str, display_name: str | None = None) -> "CodedValue":
        """공식/프로젝트가 채택한 code + code system이 둘 다 확정된 경우."""
        return cls(state="known", code=code, code_system=code_system, display_name=display_name)

    @classmethod
    def unknown(cls, *, original_text: str) -> "CodedValue":
        """concept 자체의 표준 code를 확인하지 못한 경우 - code/code_system/
        raw_code를 전혀 갖지 않는다(값이 있는데 모른다는 raw_unverified와
        구조적으로 다름)."""
        return cls(state="unknown", null_flavor="UNK", original_text=original_text)

    @classmethod
    def raw_unverified(cls, *, raw_code: str, original_text: str | None = None) -> "CodedValue":
        """raw code는 있으나 authoritative code system을 확정할 수 없는
        경우(예: Diagnosis.code="E11.9"). code_system을 추측해 채우지
        않는다 - KCD/ICD-10/SNOMED 중 하나로 단정하지 않는다."""
        return cls(state="raw_unverified", raw_code=raw_code, original_text=original_text)


@dataclass(frozen=True)
class PhysicalQuantity:
    """PQ 표현. unit은 이미 정규화된(또는 정규화를 시도했지만 실패해
    원본을 그대로 보존한) canonical 문자열이다(HL7-2 §12 unit 정규화는
    terminology.py 책임이고, 이 타입은 그 결과만 담는다)."""

    value: str
    unit: str


@dataclass(frozen=True)
class TimePoint:
    """TS 표현. 이 프로젝트의 측정 시각은 항상 timezone-aware datetime
    이어야 한다 - naive datetime은 UTC/KST 어느 쪽인지 알 수 없어
    export 시점마다 다른 문자열이 될 위험(HL7-2 §26 determinism)이
    있으므로 생성 시점에 거부한다."""

    value: datetime

    def __post_init__(self) -> None:
        if self.value.tzinfo is None:
            raise ValueError("TimePoint.value는 timezone-aware datetime이어야 합니다.")


@dataclass(frozen=True)
class TimeInterval:
    """IVL_TS 표현. high가 None이면 "진행 중"(예: Encounter.end_time
    없음)이라는 의미다(HL7-2 §7)."""

    low: TimePoint
    high: TimePoint | None = None


@dataclass(frozen=True)
class CdaObservation:
    """단일 관찰(VitalSign 단일값/LabResult/Diagnosis/BP의 수축기·이완기
    각각)을 표현한다. reference_range/warnings 등 선택 필드는 Mapper가
    필요한 경우에만 채운다."""

    identifier: Identifier
    code: CodedValue
    value: CodedValue | PhysicalQuantity
    effective_time: TimePoint
    reference_range_low: PhysicalQuantity | None = None
    reference_range_high: PhysicalQuantity | None = None


@dataclass(frozen=True)
class CdaOrganizer:
    """혈압 Organizer 표현. components는 schema상 0..*이지만(HL7-1A §12),
    이 프로젝트에서 "혈압"이라는 의미를 가지려면 정확히 2개(수축기+
    이완기)여야 한다 - 1개짜리 Organizer는 만들지 않는다(HL7-2 §11:
    하나만 있으면 Organizer 대신 단일 Observation으로 승격시킨다)."""

    identifier: Identifier
    code: CodedValue
    components: tuple[CdaObservation, ...]

    def __post_init__(self) -> None:
        if len(self.components) != 2:
            raise ValueError(
                f"CdaOrganizer.components는 정확히 2개여야 합니다(받은 개수: {len(self.components)})."
            )


@dataclass(frozen=True)
class CdaNarrative:
    """Section.text에 들어갈 사람이 읽는 내용의 논리적 구조. rows는
    표/목록의 각 행(문자열 튜플)이고, paragraph는 Patient Narrative처럼
    통짜 텍스트일 때 쓴다. 둘 중 하나만 채운다 - markup 문자열이 아니라
    plain text만 담는다(실제 XML escape/렌더링은 exporter 책임)."""

    title: str
    table_header: tuple[str, ...] | None = None
    rows: tuple[tuple[str, ...], ...] = ()
    paragraph: str | None = None


@dataclass(frozen=True)
class CdaSection:
    """4개 MVP Section(Vital Signs/Results/Problems/Patient Narrative)
    중 하나. code가 None이면 공식 코드를 생략한다는 뜻이다(HL7-3 §12:
    Section.code는 CDA Core상 0..1이라 미확정 terminology를 억지로
    nullFlavor로 표현하지 않고 그냥 생략한다)."""

    title: str
    narrative: CdaNarrative
    entries: tuple[CdaObservation | CdaOrganizer, ...] = ()
    code: CodedValue | None = None


@dataclass(frozen=True)
class CdaPatient:
    """recordTarget/patientRole/patient 표현. administrativeGenderCode는
    MVP에서 생략한다(HL7-1A §7 Patient.sex DEFERRED 결정) - 이 타입에는
    그 필드 자체가 없다. birth_time은 TimePoint(datetime)가 아니라
    date다 - 실제로 아는 정보는 "생년월일"(일 단위)뿐이고, 모르는
    시각을 자정 등으로 지어내 TS에 거짓 정밀도를 부여하지 않는다."""

    identifier: Identifier
    name: str
    birth_time: date | None = None


@dataclass(frozen=True)
class CdaAuthor:
    """author/assignedAuthor 표현."""

    identifier: Identifier
    time: TimePoint


@dataclass(frozen=True)
class CdaCustodian:
    """custodian/assignedCustodian/representedCustodianOrganization
    표현. Organization DB 모델이 없으므로 이름/식별자는 전부
    system config에서 온다(HL7-3 §7)."""

    identifier: Identifier
    organization_name: str


@dataclass(frozen=True)
class CdaEncounter:
    """componentOf/encompassingEncounter 표현. high가 None이면 진행
    중인 Encounter라는 뜻이다."""

    identifier: Identifier
    effective_time: TimeInterval


@dataclass(frozen=True)
class CdaDocument:
    """CDA 문서 전체의 IR 루트. effective_time은 export 시각이 아니라
    report.reviewed_at으로 고정해야 한다(HL7-2 §26 determinism) - 이
    타입 자체는 그 값을 강제하지 않지만 Mapper가 그 책임을 진다."""

    document_id: Identifier
    code: CodedValue
    title: str
    effective_time: TimePoint
    confidentiality_code: CodedValue
    language_code: str
    patient: CdaPatient
    author: CdaAuthor
    custodian: CdaCustodian
    encounter: CdaEncounter
    # 기본값 ()는 map_document_header()가 Section 조립 전에 먼저 Header
    # 부분만 채울 수 있게 한다 - map_document()가 최종적으로 실제
    # Section 목록으로 교체한다(dataclasses.replace).
    sections: tuple[CdaSection, ...] = ()
