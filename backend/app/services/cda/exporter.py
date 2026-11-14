"""HL7-4A: CDA Exporter.

CDA Intermediate Representation -> schema-order-correct XML bytes.
이 모듈만 CDA XML 태그/네임스페이스를 안다(HL7-2 §7/§17). DB, AI,
authorization, report 상태 검사, terminology 추측, 현재 시각을 전혀
쓰지 않는다 - 입력(CdaDocument)에 이미 고정된 값만 그대로 직렬화한다.

이 모듈은 lxml로 **직렬화**만 한다 - 공식 CDA R2.0 XSD에 대한 schema
validation은 절대 하지 않는다(Gate C 미해결, HL7-3A). "XSD validated"를
주장하지 않는다 - well-formed XML 생성까지만 책임진다.
"""

from __future__ import annotations

from datetime import datetime

from lxml import etree

from app.services.cda.models import (
    CdaDocument,
    CdaNarrative,
    CdaObservation,
    CdaOrganizer,
    CdaSection,
    CodedValue,
    Identifier,
    PhysicalQuantity,
    TimeInterval,
    TimePoint,
)

# HL7-1A에서 확인한 공식 네임스페이스(POCD_MT000040.xsd targetNamespace)
# - 특정 Implementation Guide의 추가 네임스페이스(예: sdtc)는 넣지
# 않는다(HL7-3 §19).
_CDA_NS = "urn:hl7-org:v3"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
_NSMAP = {None: _CDA_NS, "xsi": _XSI_NS}


def _qname(tag: str) -> str:
    return f"{{{_CDA_NS}}}{tag}"


def _ts_value(value: datetime) -> str:
    """TS 리터럴 - 고정 포맷(application constant), config 아님(HL7-3
    §20)."""
    return value.strftime("%Y%m%d%H%M%S%z")


def _set_ii(elem: etree._Element, identifier: Identifier) -> None:
    elem.set("root", identifier.root)
    if identifier.extension is not None:
        elem.set("extension", identifier.extension)


def _coded_element(tag: str, coded: CodedValue, *, xsi_type: str | None = None) -> etree._Element:
    """CodedValue의 3-state(HL7-2 §9/§11)를 CD/CE XML로 직렬화한다.
    raw_unverified는 codeSystem을 추측해 채우지 않는다."""
    elem = etree.Element(_qname(tag))
    if xsi_type:
        elem.set(f"{{{_XSI_NS}}}type", xsi_type)

    if coded.state == "known":
        elem.set("code", coded.code)
        elem.set("codeSystem", coded.code_system)
        if coded.display_name:
            elem.set("displayName", coded.display_name)
    elif coded.state == "unknown":
        elem.set("nullFlavor", coded.null_flavor)
        if coded.original_text:
            original_text_elem = etree.SubElement(elem, _qname("originalText"))
            original_text_elem.text = coded.original_text
    else:  # raw_unverified
        elem.set("code", coded.raw_code)
        if coded.original_text:
            original_text_elem = etree.SubElement(elem, _qname("originalText"))
            original_text_elem.text = coded.original_text
    return elem


def _pq_element(tag: str, pq: PhysicalQuantity, *, xsi_type: str | None = None) -> etree._Element:
    elem = etree.Element(_qname(tag))
    if xsi_type:
        elem.set(f"{{{_XSI_NS}}}type", xsi_type)
    elem.set("value", pq.value)
    elem.set("unit", pq.unit)
    return elem


def _observation_value_element(value: CodedValue | PhysicalQuantity) -> etree._Element:
    # Observation.value는 abstract(ANY) 자리라 xsi:type으로 실제
    # datatype을 명시해야 한다(HL7-1A/HL7-2 §17/§19).
    if isinstance(value, PhysicalQuantity):
        return _pq_element("value", value, xsi_type="PQ")
    return _coded_element("value", value, xsi_type="CD")


def _ivl_ts_element(tag: str, interval: TimeInterval) -> etree._Element:
    elem = etree.Element(_qname(tag))
    low = etree.SubElement(elem, _qname("low"))
    low.set("value", _ts_value(interval.low.value))
    if interval.high is not None:
        high = etree.SubElement(elem, _qname("high"))
        high.set("value", _ts_value(interval.high.value))
    return elem


def _observation_element(observation: CdaObservation) -> etree._Element:
    elem = etree.Element(_qname("observation"))
    # ActClass "OBS"/ActMood "EVN"은 voc.xsd에서 실존 enum으로 확인됨
    # (HL7-1A) - ActStatus와 달리 추측이 아니다.
    elem.set("classCode", "OBS")
    elem.set("moodCode", "EVN")

    id_elem = etree.SubElement(elem, _qname("id"))
    _set_ii(id_elem, observation.identifier)

    elem.append(_coded_element("code", observation.code))

    # Observation.statusCode는 CDA Core상 0..1(선택)이고, 공식 ActStatus
    # 허용값을 확인하지 못했다(HL7-1A/HL7-3A) - 값을 추측해 넣지 않고
    # 아예 생략한다(선택 element이므로 생략이 schema-valid).
    elem.append(_ts_element_simple("effectiveTime", observation.effective_time))
    elem.append(_observation_value_element(observation.value))

    if observation.reference_range_low is not None and observation.reference_range_high is not None:
        reference_range = etree.SubElement(elem, _qname("referenceRange"))
        observation_range = etree.SubElement(reference_range, _qname("observationRange"))
        range_value = etree.SubElement(observation_range, _qname("value"))
        range_value.set(f"{{{_XSI_NS}}}type", "IVL_PQ")
        low = etree.SubElement(range_value, _qname("low"))
        low.set("value", observation.reference_range_low.value)
        low.set("unit", observation.reference_range_low.unit)
        high = etree.SubElement(range_value, _qname("high"))
        high.set("value", observation.reference_range_high.value)
        high.set("unit", observation.reference_range_high.unit)

    return elem


def _ts_element_simple(tag: str, time_point: TimePoint) -> etree._Element:
    elem = etree.Element(_qname(tag))
    elem.set("value", _ts_value(time_point.value))
    return elem


def _organizer_element(organizer: CdaOrganizer) -> etree._Element:
    elem = etree.Element(_qname("organizer"))
    elem.set("classCode", "CLUSTER")
    elem.set("moodCode", "EVN")

    id_elem = etree.SubElement(elem, _qname("id"))
    _set_ii(id_elem, organizer.identifier)

    elem.append(_coded_element("code", organizer.code))

    # Organizer.statusCode는 1..1 필수(HL7-1A §12)이지만 공식 ActStatus
    # 허용값은 확인하지 못했다 - "completed" 등을 추측해 넣지 않고,
    # 필수 element는 채우되 허위 코드는 넣지 않기 위해 nullFlavor="UNK"
    # 를 쓴다.
    status_code_elem = etree.SubElement(elem, _qname("statusCode"))
    status_code_elem.set("nullFlavor", "UNK")

    for component_observation in organizer.components:
        component_elem = etree.SubElement(elem, _qname("component"))
        component_elem.append(_observation_element(component_observation))

    return elem


def _entry_element(entry: CdaObservation | CdaOrganizer) -> etree._Element:
    entry_elem = etree.Element(_qname("entry"))
    if isinstance(entry, CdaOrganizer):
        entry_elem.append(_organizer_element(entry))
    else:
        entry_elem.append(_observation_element(entry))
    return entry_elem


def _narrative_text_element(narrative: CdaNarrative) -> etree._Element:
    """NarrativeBlock의 공식 허용 엘리먼트(paragraph/table/list)만
    쓴다 - 임의 HTML을 넣지 않는다(HL7-1A/HL7-2 §20)."""
    text_elem = etree.Element(_qname("text"))
    if narrative.paragraph is not None:
        paragraph_elem = etree.SubElement(text_elem, _qname("paragraph"))
        paragraph_elem.text = narrative.paragraph
    elif narrative.table_header:
        table_elem = etree.SubElement(text_elem, _qname("table"))
        thead = etree.SubElement(table_elem, _qname("thead"))
        header_row = etree.SubElement(thead, _qname("tr"))
        for header_cell in narrative.table_header:
            th = etree.SubElement(header_row, _qname("th"))
            th.text = header_cell
        tbody = etree.SubElement(table_elem, _qname("tbody"))
        for row in narrative.rows:
            tr = etree.SubElement(tbody, _qname("tr"))
            for cell in row:
                td = etree.SubElement(tr, _qname("td"))
                td.text = cell
    else:
        list_elem = etree.SubElement(text_elem, _qname("list"))
        for row in narrative.rows:
            item_elem = etree.SubElement(list_elem, _qname("item"))
            item_elem.text = " ".join(row)
    return text_elem


def _section_element(section: CdaSection) -> etree._Element:
    section_elem = etree.Element(_qname("section"))
    if section.code is not None:
        section_elem.append(_coded_element("code", section.code))
    title_elem = etree.SubElement(section_elem, _qname("title"))
    title_elem.text = section.title
    section_elem.append(_narrative_text_element(section.narrative))
    for entry in section.entries:
        section_elem.append(_entry_element(entry))
    return section_elem


def export_document(document: CdaDocument) -> bytes:
    """CdaDocument -> well-formed CDA XML bytes. element 순서는
    HL7-1A에서 확인한 normative sequence를 그대로 따른다. pretty-print는
    쓰지 않는다 - NarrativeBlock mixed-content 공백 오염을 피하고
    byte-for-byte determinism을 지킨다(HL7-2 §18/HL7-3 §19)."""
    root = etree.Element(_qname("ClinicalDocument"), nsmap=_NSMAP)

    type_id_elem = etree.SubElement(root, _qname("typeId"))
    type_id_elem.set("root", "2.16.840.1.113883.1.3")
    type_id_elem.set("extension", "POCD_HD000040")

    id_elem = etree.SubElement(root, _qname("id"))
    _set_ii(id_elem, document.document_id)

    root.append(_coded_element("code", document.code))

    title_elem = etree.SubElement(root, _qname("title"))
    title_elem.text = document.title

    root.append(_ts_element_simple("effectiveTime", document.effective_time))
    root.append(_coded_element("confidentialityCode", document.confidentiality_code))

    language_code_elem = etree.SubElement(root, _qname("languageCode"))
    language_code_elem.set("code", document.language_code)

    record_target = etree.SubElement(root, _qname("recordTarget"))
    patient_role = etree.SubElement(record_target, _qname("patientRole"))
    patient_role_id = etree.SubElement(patient_role, _qname("id"))
    _set_ii(patient_role_id, document.patient.identifier)
    patient_elem = etree.SubElement(patient_role, _qname("patient"))
    name_elem = etree.SubElement(patient_elem, _qname("name"))
    name_elem.text = document.patient.name
    if document.patient.birth_time is not None:
        birth_time_elem = etree.SubElement(patient_elem, _qname("birthTime"))
        birth_time_elem.set("value", document.patient.birth_time.strftime("%Y%m%d"))

    author_elem = etree.SubElement(root, _qname("author"))
    author_time_elem = etree.SubElement(author_elem, _qname("time"))
    author_time_elem.set("value", _ts_value(document.author.time.value))
    assigned_author = etree.SubElement(author_elem, _qname("assignedAuthor"))
    assigned_author_id = etree.SubElement(assigned_author, _qname("id"))
    _set_ii(assigned_author_id, document.author.identifier)

    custodian_elem = etree.SubElement(root, _qname("custodian"))
    assigned_custodian = etree.SubElement(custodian_elem, _qname("assignedCustodian"))
    represented_custodian_org = etree.SubElement(
        assigned_custodian, _qname("representedCustodianOrganization")
    )
    custodian_id_elem = etree.SubElement(represented_custodian_org, _qname("id"))
    _set_ii(custodian_id_elem, document.custodian.identifier)
    custodian_name_elem = etree.SubElement(represented_custodian_org, _qname("name"))
    custodian_name_elem.text = document.custodian.organization_name

    component_of = etree.SubElement(root, _qname("componentOf"))
    encompassing_encounter = etree.SubElement(component_of, _qname("encompassingEncounter"))
    encounter_id_elem = etree.SubElement(encompassing_encounter, _qname("id"))
    _set_ii(encounter_id_elem, document.encounter.identifier)
    encompassing_encounter.append(_ivl_ts_element("effectiveTime", document.encounter.effective_time))

    component_elem = etree.SubElement(root, _qname("component"))
    structured_body = etree.SubElement(component_elem, _qname("structuredBody"))
    for section in document.sections:
        section_component = etree.SubElement(structured_body, _qname("component"))
        section_component.append(_section_element(section))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=False)
