import { TimelineItem } from "../../api/timeline";
import { formatVitalSignValue, VitalType as VitalSignType } from "../vitalSign/formatVitalSign";
import SectionCard from "../ui/SectionCard";

export type EncounterSummary = {
  encounterItem: TimelineItem;
  vitalSigns: TimelineItem[];
  labResults: TimelineItem[];
  diagnoses: TimelineItem[];
};

// UX-1B: 이미 GET /patients/{id}/timeline 응답으로 받은 TimelineItem[]만
// encounter_id로 client-side grouping한다 — 추가 fetch/신규 endpoint 없음.
// encounter_id가 없는 TimelineItem은 존재하지 않는다(Backend contract상
// 항상 number) - 다만 어떤 encounter_id 그룹에 ENCOUNTER 항목 자체가
// 없다면(비정상 응답) header를 VitalSign 등에서 지어내지 않고 그 그룹
// 전체를 Summary에서 제외한다.
export function groupTimelineByEncounter(timeline: TimelineItem[]): EncounterSummary[] {
  const encounterItemsById = new Map<number, TimelineItem>();
  for (const item of timeline) {
    if (item.event_type === "ENCOUNTER") {
      encounterItemsById.set(item.encounter_id, item);
    }
  }

  const summaries: EncounterSummary[] = [];
  const seenEncounterIds = new Set<number>();

  for (const item of timeline) {
    const encounterId = item.encounter_id;
    if (seenEncounterIds.has(encounterId)) continue;
    seenEncounterIds.add(encounterId);

    const encounterItem = encounterItemsById.get(encounterId);
    if (!encounterItem) continue;

    summaries.push({
      encounterItem,
      // 원본 timeline 배열 순서를 그대로 보존한다(재정렬 없음, 임의 축약 없음).
      vitalSigns: timeline.filter((i) => i.encounter_id === encounterId && i.event_type === "VITAL_SIGN"),
      labResults: timeline.filter((i) => i.encounter_id === encounterId && i.event_type === "LAB_RESULT"),
      diagnoses: timeline.filter((i) => i.encounter_id === encounterId && i.event_type === "DIAGNOSIS"),
    });
  }

  // 가장 최근 Encounter 먼저 - 기존 flat Timeline이 이미 따르는 백엔드
  // 정렬 규칙(event_time DESC, tie-break encounter_id DESC)과 일치시켜
  // UX 일관성을 유지한다.
  return [...summaries].sort((a, b) => {
    const timeDiff =
      new Date(b.encounterItem.event_time).getTime() - new Date(a.encounterItem.event_time).getTime();
    if (timeDiff !== 0) return timeDiff;
    return b.encounterItem.encounter_id - a.encounterItem.encounter_id;
  });
}

function renderVitalSignLine(item: TimelineItem): string {
  const value =
    item.vital_type && item.value && item.unit
      ? formatVitalSignValue(item.vital_type as VitalSignType, item.value, item.value_secondary ?? null, item.unit)
      : item.summary;
  return `${item.title}: ${value}`;
}

interface EncounterSummaryCardProps {
  summary: EncounterSummary;
}

// UX-1B MVP: 활력징후/검사결과/진단만 보여준다(Section 8). LabResult는
// Backend가 이미 합성해 보낸 raw summary 문자열을 그대로 쓴다 - HIGH/LOW/
// NORMAL 판정/배지는 UX-1C에서만 다룬다(이번 범위 아님). Diagnosis도
// code/description을 그대로 보여주고 KCD/ICD-10/SNOMED 같은 code system
// 이름을 새로 붙이지 않는다. 비어 있는 카테고리는 섹션 자체를 숨긴다
// (카드마다 반복되는 EmptyState를 피하기 위한 선택, §20 Option A).
// 이번 첫 구현에서는 "진료참고 보고서 생성" action을 추가하지 않는다
// (§14 최소 안전 범위 - 기존 flat Timeline에서만 계속 제공).
export default function EncounterSummaryCard({ summary }: EncounterSummaryCardProps) {
  const { encounterItem, vitalSigns, labResults, diagnoses } = summary;
  // 카드 header 위계: 날짜(heading) → 진료과·방문 유형(보조 문구).
  // 표시하는 값과 순서는 기존과 같다.
  const headerTitle = new Date(encounterItem.event_time).toLocaleString();
  const headerContext = `${encounterItem.department} · ${encounterItem.title}`;

  return (
    <SectionCard title={headerTitle} headingLevel={3} className="encounter-summary-card">
      <p className="encounter-summary-card__context">{headerContext}</p>

      {vitalSigns.length > 0 && (
        <div className="encounter-summary-card__group">
          <h4>활력징후</h4>
          <ul>
            {vitalSigns.map((item) => (
              <li key={item.id}>{renderVitalSignLine(item)}</li>
            ))}
          </ul>
        </div>
      )}

      {labResults.length > 0 && (
        <div className="encounter-summary-card__group">
          <h4>검사결과</h4>
          <ul>
            {labResults.map((item) => (
              <li key={item.id}>
                {item.title}: {item.summary}
              </li>
            ))}
          </ul>
        </div>
      )}

      {diagnoses.length > 0 && (
        <div className="encounter-summary-card__group">
          <h4>진단</h4>
          <ul>
            {diagnoses.map((item) => (
              <li key={item.id}>
                {item.title} ({item.summary})
              </li>
            ))}
          </ul>
        </div>
      )}
    </SectionCard>
  );
}
