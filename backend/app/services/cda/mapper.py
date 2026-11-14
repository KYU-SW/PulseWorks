"""HL7-4A: CDA Mapper.

CdaExportInput(§7 adapter 출력) -> CDA Intermediate Representation.
결정적(deterministic) 순수 함수만 둔다 - DB, AI, XML을 전혀 모른다
(HL7-2 §3).
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from decimal import Decimal

from app.core.config import Settings
from app.models.enums import VitalType
from app.schemas.clinical_report import SnapshotDiagnosis, SnapshotLabResult, SnapshotVitalSign
from app.services.cda.adapter import CdaExportInput
from app.services.cda.errors import CdaWarning
from app.services.cda.models import (
    CdaAuthor,
    CdaCustodian,
    CdaDocument,
    CdaEncounter,
    CdaNarrative,
    CdaObservation,
    CdaOrganizer,
    CdaPatient,
    CdaSection,
    CodedValue,
    Identifier,
    PhysicalQuantity,
    TimeInterval,
    TimePoint,
)
from app.services.cda.terminology import (
    BLOOD_PRESSURE_DIASTOLIC_LOINC,
    BLOOD_PRESSURE_LABEL,
    BLOOD_PRESSURE_PANEL_LOINC,
    BLOOD_PRESSURE_SYSTOLIC_LOINC,
    CDA_CONFIDENTIALITY_CODE,
    CDA_DOCUMENT_CODE_ORIGINAL_TEXT,
    CDA_DOCUMENT_TITLE,
    normalize_unit,
    vital_type_coded_value,
)

_NO_DATA_PLACEHOLDER = "기록된 정보가 없습니다"


def _format_timestamp(value: datetime) -> str:
    """고정 포맷(application constant) - AI/로캘 의존 없음(HL7-2 §16)."""
    return value.strftime("%Y-%m-%d %H:%M")

_LOINC_CODE_SYSTEM_OID = "2.16.840.1.113883.6.1"


def _bp_coded_value(code: str) -> CodedValue:
    return CodedValue.known(code=code, code_system=_LOINC_CODE_SYSTEM_OID)


def build_blood_pressure_entry(
    *,
    value: Decimal | None,
    value_secondary: Decimal | None,
    source_record_id: str,
    entry_id_root: str,
    unit: str,
    measured_at: datetime,
) -> tuple[CdaOrganizer | None, CdaWarning | None]:
    """HL7-4A §14 정책: 둘 다 있어야 Organizer(수축기+이완기)를 만든다.
    하나라도 없으면 Organizer도, 단일 Observation으로의 재해석도 하지
    않고 entry 자체를 None으로 생략한 채 structured warning만 반환한다.
    warning 메시지에는 환자 식별정보/실제 측정값을 담지 않는다(HL7-4A
    §15)."""
    if value is None or value_secondary is None:
        warning = CdaWarning(
            code="INCOMPLETE_BLOOD_PRESSURE",
            source_type="vital_sign",
            source_record_id=source_record_id,
            message="혈압 수축기/이완기 중 하나가 없어 해당 Entry를 생략했습니다.",
        )
        return None, warning

    normalized_unit = normalize_unit(unit)
    effective_time = TimePoint(value=measured_at)

    systolic = CdaObservation(
        identifier=Identifier(root=entry_id_root, extension=f"{source_record_id}:systolic"),
        code=_bp_coded_value(BLOOD_PRESSURE_SYSTOLIC_LOINC),
        value=PhysicalQuantity(value=str(value), unit=normalized_unit),
        effective_time=effective_time,
    )
    diastolic = CdaObservation(
        identifier=Identifier(root=entry_id_root, extension=f"{source_record_id}:diastolic"),
        code=_bp_coded_value(BLOOD_PRESSURE_DIASTOLIC_LOINC),
        value=PhysicalQuantity(value=str(value_secondary), unit=normalized_unit),
        effective_time=effective_time,
    )
    organizer = CdaOrganizer(
        identifier=Identifier(root=entry_id_root, extension=source_record_id),
        code=_bp_coded_value(BLOOD_PRESSURE_PANEL_LOINC),
        components=(systolic, diastolic),
    )
    return organizer, None


def _build_single_vital_observation(
    vital_sign: SnapshotVitalSign, *, entry_id_root: str, vital_type: VitalType, source_record_id: str
) -> CdaObservation:
    return CdaObservation(
        identifier=Identifier(root=entry_id_root, extension=source_record_id),
        code=vital_type_coded_value(vital_type),
        value=PhysicalQuantity(value=str(vital_sign.value), unit=normalize_unit(vital_sign.unit)),
        effective_time=TimePoint(value=vital_sign.measured_at),
    )


def map_vital_signs(
    vital_signs: tuple[SnapshotVitalSign, ...], *, entry_id_root: str
) -> tuple[tuple[CdaObservation | CdaOrganizer, ...], tuple[CdaWarning, ...]]:
    """7종 VitalSign 전체를 결정적으로 변환한다. 입력 순서를 그대로
    유지한다(ordering은 호출자/Section 조립 단계의 책임)."""
    entries: list[CdaObservation | CdaOrganizer] = []
    warnings: list[CdaWarning] = []

    for vital_sign in vital_signs:
        vital_type = VitalType(vital_sign.vital_type)
        source_record_id = f"vital_sign:{vital_sign.id}"

        if vital_type is VitalType.BLOOD_PRESSURE:
            entry, warning = build_blood_pressure_entry(
                value=vital_sign.value,
                value_secondary=vital_sign.value_secondary,
                source_record_id=source_record_id,
                entry_id_root=entry_id_root,
                unit=vital_sign.unit,
                measured_at=vital_sign.measured_at,
            )
            if entry is not None:
                entries.append(entry)
            if warning is not None:
                warnings.append(warning)
        else:
            entries.append(
                _build_single_vital_observation(
                    vital_sign,
                    entry_id_root=entry_id_root,
                    vital_type=vital_type,
                    source_record_id=source_record_id,
                )
            )

    return tuple(entries), tuple(warnings)


def build_reference_range(
    reference_low: float | None, reference_high: float | None, *, unit: str
) -> tuple[PhysicalQuantity | None, PhysicalQuantity | None]:
    """둘 다 있어야 reference range를 만든다(HL7-4A §16) - 한쪽만 있으면
    거짓 범위를 만들지 않고 둘 다 생략한다. 현재 SnapshotLabResult는
    DB NOT NULL이라 실제로는 항상 둘 다 존재하지만, Mapper 계약
    자체는 방어적으로 설계한다."""
    if reference_low is None or reference_high is None:
        return None, None
    normalized_unit = normalize_unit(unit)
    return (
        PhysicalQuantity(value=str(reference_low), unit=normalized_unit),
        PhysicalQuantity(value=str(reference_high), unit=normalized_unit),
    )


def map_lab_results(
    lab_results: tuple[SnapshotLabResult, ...], *, entry_id_root: str
) -> tuple[CdaObservation, ...]:
    """SnapshotLabResult -> CdaObservation. 표준 검사 코드가 미확정이라
    terminology는 항상 UNKNOWN 상태(nullFlavor="UNK"+originalText)로
    표현한다 - HIRA EDI/LOINC 중 하나를 근거 없이 선택하지 않는다
    (HL7-1/1A). LabResult.status(LOW/HIGH/NORMAL/UNKNOWN)는 CdaObservation
    에 대응하는 필드가 없어 구조적으로 CDA에 노출되지 않는다."""
    entries = []
    for lab_result in lab_results:
        reference_low, reference_high = build_reference_range(
            lab_result.reference_low, lab_result.reference_high, unit=lab_result.unit
        )
        entries.append(
            CdaObservation(
                identifier=Identifier(root=entry_id_root, extension=f"lab_result:{lab_result.id}"),
                code=CodedValue.unknown(original_text=lab_result.test_name),
                value=PhysicalQuantity(
                    value=str(lab_result.value), unit=normalize_unit(lab_result.unit)
                ),
                effective_time=TimePoint(value=lab_result.measured_at),
                reference_range_low=reference_low,
                reference_range_high=reference_high,
            )
        )
    return tuple(entries)


def map_diagnoses(
    diagnoses: tuple[SnapshotDiagnosis, ...], *, entry_id_root: str
) -> tuple[CdaObservation, ...]:
    """SnapshotDiagnosis -> CdaObservation. Observation.code는 "이
    observation의 종류"(UNKNOWN, 가짜 메타코드 없음)이고,
    Observation.value가 실제 diagnosis concept(raw_unverified: 원본
    code를 손실 없이 보존하되 code_system은 KCD/ICD-10/SNOMED 중
    아무것도 추측하지 않음, HL7-1/1A/HL7-2 §15)이다."""
    entries = []
    for diagnosis in diagnoses:
        entries.append(
            CdaObservation(
                identifier=Identifier(root=entry_id_root, extension=f"diagnosis:{diagnosis.id}"),
                code=CodedValue.unknown(original_text="진단"),
                value=CodedValue.raw_unverified(
                    raw_code=diagnosis.code, original_text=diagnosis.description
                ),
                effective_time=TimePoint(value=diagnosis.diagnosed_at),
            )
        )
    return tuple(entries)


def map_document_header(export_input: CdaExportInput, settings: Settings) -> CdaDocument:
    """CdaExportInput + CDA Settings -> Header 부분만 채운 CdaDocument
    (sections=()). effective_time은 export 시각(datetime.now())이 아니라
    reviewed_at을 쓴다(HL7-2 §26 determinism) - reviewed_at이 없으면
    "지금"으로 대체하지 않고 즉시 거부한다. legalAuthenticator/
    authenticator/realmCode/setId/versionNumber는 CdaDocument 타입
    자체에 필드가 없어 구조적으로 생성될 수 없다."""
    if export_input.reviewed_at is None:
        raise ValueError(
            "ClinicalDocument.effectiveTime에는 reviewed_at이 필요합니다 - "
            "export 시각(현재 시각)을 대신 쓰지 않습니다."
        )

    patient = CdaPatient(
        identifier=Identifier(root=settings.cda_patient_id_root, extension=export_input.patient.mrn),
        name=export_input.patient.name,
        birth_time=export_input.patient.birth_date,
    )

    encounter_source = export_input.encounter
    encounter = CdaEncounter(
        identifier=Identifier(root=settings.cda_encounter_id_root, extension=str(encounter_source.id)),
        effective_time=TimeInterval(
            low=TimePoint(value=encounter_source.start_time),
            high=TimePoint(value=encounter_source.end_time) if encounter_source.end_time else None,
        ),
    )

    author = CdaAuthor(
        identifier=Identifier(
            root=settings.cda_author_id_root, extension=str(export_input.created_by_user_id)
        ),
        time=TimePoint(value=export_input.created_at),
    )

    custodian = CdaCustodian(
        identifier=Identifier(
            root=settings.cda_custodian_id_root, extension=settings.cda_custodian_id_extension
        ),
        organization_name=settings.cda_custodian_name,
    )

    return CdaDocument(
        document_id=Identifier(root=settings.cda_document_id_root, extension=str(export_input.report_id)),
        code=CDA_DOCUMENT_CODE_ORIGINAL_TEXT,
        title=CDA_DOCUMENT_TITLE,
        effective_time=TimePoint(value=export_input.reviewed_at),
        confidentiality_code=CDA_CONFIDENTIALITY_CODE,
        language_code=settings.cda_language_code,
        patient=patient,
        author=author,
        custodian=custodian,
        encounter=encounter,
        sections=(),
    )


def _build_vital_signs_section(
    entries: tuple[CdaObservation | CdaOrganizer, ...],
) -> CdaSection:
    """Narrative row는 Structured Entry와 같은 IR 값에서 파생한다(HL7-4A
    §19) - Snapshot을 따로 다시 계산하지 않는다."""
    rows: list[tuple[str, ...]] = []
    for entry in entries:
        if isinstance(entry, CdaOrganizer):
            systolic, diastolic = entry.components
            rows.append(
                (
                    BLOOD_PRESSURE_LABEL,
                    f"{systolic.value.value}/{diastolic.value.value} {systolic.value.unit}",
                    _format_timestamp(systolic.effective_time.value),
                )
            )
        else:
            rows.append(
                (
                    entry.code.display_name or "",
                    f"{entry.value.value} {entry.value.unit}",
                    _format_timestamp(entry.effective_time.value),
                )
            )
    if not rows:
        rows = [(_NO_DATA_PLACEHOLDER, "", "")]

    narrative = CdaNarrative(title="생체 징후", table_header=("항목", "값", "측정시각"), rows=tuple(rows))
    return CdaSection(title="생체 징후", narrative=narrative, entries=entries)


def _build_results_section(entries: tuple[CdaObservation, ...]) -> CdaSection:
    rows: list[tuple[str, ...]] = []
    for entry in entries:
        range_text = ""
        if entry.reference_range_low is not None and entry.reference_range_high is not None:
            range_text = (
                f"{entry.reference_range_low.value}-{entry.reference_range_high.value} "
                f"{entry.reference_range_low.unit}"
            )
        rows.append(
            (
                entry.code.original_text or "",
                f"{entry.value.value} {entry.value.unit}",
                range_text,
                _format_timestamp(entry.effective_time.value),
            )
        )
    if not rows:
        rows = [(_NO_DATA_PLACEHOLDER, "", "", "")]

    narrative = CdaNarrative(
        title="검사결과", table_header=("검사명", "값", "참고범위", "측정시각"), rows=tuple(rows)
    )
    return CdaSection(title="검사결과", narrative=narrative, entries=entries)


def _build_problems_section(entries: tuple[CdaObservation, ...]) -> CdaSection:
    rows: list[tuple[str, ...]] = []
    for entry in entries:
        value = entry.value
        assert isinstance(value, CodedValue)
        rows.append((f"{value.original_text} ({value.raw_code})", _format_timestamp(entry.effective_time.value)))
    if not rows:
        rows = [(_NO_DATA_PLACEHOLDER, "")]

    narrative = CdaNarrative(title="문제 목록", rows=tuple(rows))
    return CdaSection(title="문제 목록", narrative=narrative, entries=entries)


def _build_patient_narrative_section(narrative_text: str | None) -> CdaSection:
    """approved report narrative만 plain text로 쓴다 - AI markup을
    신뢰하지 않는다(HL7-2 §15/§16, 실제 escape는 exporter 책임)."""
    narrative = CdaNarrative(title="환자 서술", paragraph=narrative_text or "")
    return CdaSection(title="환자 서술", narrative=narrative, entries=())


def map_document(
    export_input: CdaExportInput, settings: Settings
) -> tuple[CdaDocument, tuple[CdaWarning, ...]]:
    """전체 CDA Mapper 조립 - Header + 4개 MVP Section(고정 순서:
    Vital Signs/Results/Problems/Patient Narrative, HL7-4A §20)."""
    header = map_document_header(export_input, settings)

    vital_entries, warnings = map_vital_signs(
        export_input.vital_signs, entry_id_root=settings.cda_entry_id_root
    )
    lab_entries = map_lab_results(export_input.lab_results, entry_id_root=settings.cda_entry_id_root)
    diagnosis_entries = map_diagnoses(export_input.diagnoses, entry_id_root=settings.cda_entry_id_root)

    sections = (
        _build_vital_signs_section(vital_entries),
        _build_results_section(lab_entries),
        _build_problems_section(diagnosis_entries),
        _build_patient_narrative_section(export_input.narrative),
    )

    document = dataclasses.replace(header, sections=sections)
    return document, warnings
