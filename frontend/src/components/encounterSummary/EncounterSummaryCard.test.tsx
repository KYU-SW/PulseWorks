import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TimelineItem } from "../../api/timeline";
import EncounterSummaryCard, { groupTimelineByEncounter } from "./EncounterSummaryCard";

// UX-1B: 이미 GET /patients/{id}/timeline 응답으로 받은 TimelineItem[]만
// 입력으로 받는 순수 grouping 함수 + 카드 렌더링 컴포넌트 테스트다. 신규
// API 호출은 이 파일 어디에도 없다 — fetch/axios/apiGet을 전혀 import하지
// 않는다.

function makeEncounterItem(overrides: Partial<TimelineItem> = {}): TimelineItem {
  return {
    id: 1,
    encounter_id: 1,
    event_type: "ENCOUNTER",
    event_time: "2026-03-10T09:00:00+00:00",
    title: "내분비내과 외래 방문",
    summary: "내분비내과 외래 방문 (합성 데이터)",
    source_type: null,
    department: "내분비내과",
    ...overrides,
  };
}

function makeVitalSignItem(overrides: Partial<TimelineItem> = {}): TimelineItem {
  return {
    id: 100,
    encounter_id: 1,
    event_type: "VITAL_SIGN",
    event_time: "2026-03-10T09:05:00+00:00",
    title: "혈압",
    summary: "132/84 mmHg",
    source_type: "INSTITUTION_GENERATED",
    department: "내분비내과",
    vital_type: "BLOOD_PRESSURE",
    value: "132",
    value_secondary: "84",
    unit: "mmHg",
    ...overrides,
  };
}

function makeLabResultItem(overrides: Partial<TimelineItem> = {}): TimelineItem {
  return {
    id: 200,
    encounter_id: 1,
    event_type: "LAB_RESULT",
    event_time: "2026-03-10T09:10:00+00:00",
    title: "HbA1c",
    summary: "7.2% (참고범위 4.0-6.0%)",
    source_type: "INSTITUTION_GENERATED",
    department: "내분비내과",
    ...overrides,
  };
}

function makeDiagnosisItem(overrides: Partial<TimelineItem> = {}): TimelineItem {
  return {
    id: 300,
    encounter_id: 1,
    event_type: "DIAGNOSIS",
    event_time: "2026-03-10T09:15:00+00:00",
    title: "2형 당뇨병",
    summary: "진단 코드: E11.9",
    source_type: "INSTITUTION_GENERATED",
    department: "내분비내과",
    ...overrides,
  };
}

describe("groupTimelineByEncounter", () => {
  // 1. 단일 Encounter -> Summary 1개
  it("produces a single summary for a single encounter", () => {
    const timeline = [makeEncounterItem(), makeVitalSignItem()];
    const summaries = groupTimelineByEncounter(timeline);
    expect(summaries).toHaveLength(1);
    expect(summaries[0].encounterItem.encounter_id).toBe(1);
  });

  // 2. Encounter 2개 -> Summary 2개
  it("produces one summary per distinct encounter_id", () => {
    const timeline = [
      makeEncounterItem({ id: 1, encounter_id: 1 }),
      makeEncounterItem({ id: 2, encounter_id: 2, event_time: "2026-03-11T09:00:00+00:00" }),
    ];
    const summaries = groupTimelineByEncounter(timeline);
    expect(summaries).toHaveLength(2);
  });

  // 3. Encounter A의 VitalSign이 Encounter B 카드에 표시되지 않음
  it("never mixes vital signs from a different encounter into another encounter's group", () => {
    const timeline = [
      makeEncounterItem({ id: 1, encounter_id: 1 }),
      makeEncounterItem({ id: 2, encounter_id: 2, event_time: "2026-03-11T09:00:00+00:00" }),
      makeVitalSignItem({ id: 101, encounter_id: 1 }),
    ];
    const summaries = groupTimelineByEncounter(timeline);
    const groupA = summaries.find((s) => s.encounterItem.encounter_id === 1)!;
    const groupB = summaries.find((s) => s.encounterItem.encounter_id === 2)!;
    expect(groupA.vitalSigns).toHaveLength(1);
    expect(groupB.vitalSigns).toHaveLength(0);
  });

  // 4. Encounter A의 LabResult가 Encounter B 카드에 표시되지 않음
  it("never mixes lab results from a different encounter into another encounter's group", () => {
    const timeline = [
      makeEncounterItem({ id: 1, encounter_id: 1 }),
      makeEncounterItem({ id: 2, encounter_id: 2, event_time: "2026-03-11T09:00:00+00:00" }),
      makeLabResultItem({ id: 201, encounter_id: 1 }),
    ];
    const summaries = groupTimelineByEncounter(timeline);
    const groupA = summaries.find((s) => s.encounterItem.encounter_id === 1)!;
    const groupB = summaries.find((s) => s.encounterItem.encounter_id === 2)!;
    expect(groupA.labResults).toHaveLength(1);
    expect(groupB.labResults).toHaveLength(0);
  });

  // 5. Encounter A의 Diagnosis가 Encounter B 카드에 표시되지 않음
  it("never mixes diagnoses from a different encounter into another encounter's group", () => {
    const timeline = [
      makeEncounterItem({ id: 1, encounter_id: 1 }),
      makeEncounterItem({ id: 2, encounter_id: 2, event_time: "2026-03-11T09:00:00+00:00" }),
      makeDiagnosisItem({ id: 301, encounter_id: 1 }),
    ];
    const summaries = groupTimelineByEncounter(timeline);
    const groupA = summaries.find((s) => s.encounterItem.encounter_id === 1)!;
    const groupB = summaries.find((s) => s.encounterItem.encounter_id === 2)!;
    expect(groupA.diagnoses).toHaveLength(1);
    expect(groupB.diagnoses).toHaveLength(0);
  });

  // 6. 한 Encounter 내부의 여러 임상 항목이 모두 유지됨(데이터 임의 축약 없음)
  it("keeps every clinical item that belongs to the same encounter", () => {
    const timeline = [
      makeEncounterItem({ id: 1, encounter_id: 1 }),
      makeVitalSignItem({ id: 101, encounter_id: 1, vital_type: "BLOOD_PRESSURE" }),
      makeVitalSignItem({
        id: 102,
        encounter_id: 1,
        title: "체온",
        vital_type: "BODY_TEMPERATURE",
        value: "36.7",
        value_secondary: null,
        unit: "Cel",
      }),
      makeLabResultItem({ id: 201, encounter_id: 1 }),
      makeLabResultItem({ id: 202, encounter_id: 1, title: "Glucose", summary: "140mg/dL (참고범위 70-110mg/dL)" }),
      makeDiagnosisItem({ id: 301, encounter_id: 1 }),
    ];
    const summaries = groupTimelineByEncounter(timeline);
    expect(summaries).toHaveLength(1);
    expect(summaries[0].vitalSigns).toHaveLength(2);
    expect(summaries[0].labResults).toHaveLength(2);
    expect(summaries[0].diagnoses).toHaveLength(1);
  });

  // 7. Encounter header에 실제 Encounter 정보가 표시됨(VitalSign 등에서 추론하지 않음)
  it("uses the real ENCOUNTER item's own fields as the group header, never inferred values", () => {
    const timeline = [
      makeEncounterItem({
        encounter_id: 1,
        title: "내분비내과 외래 방문",
        department: "내분비내과",
        event_time: "2026-03-10T09:00:00+00:00",
      }),
      makeVitalSignItem({ encounter_id: 1 }),
    ];
    const summaries = groupTimelineByEncounter(timeline);
    expect(summaries[0].encounterItem.title).toBe("내분비내과 외래 방문");
    expect(summaries[0].encounterItem.department).toBe("내분비내과");
    expect(summaries[0].encounterItem.event_time).toBe("2026-03-10T09:00:00+00:00");
  });

  // ENCOUNTER 항목이 없는 encounter_id 그룹은 제외한다(§9: fabricate 금지).
  it("excludes a group that has no ENCOUNTER item instead of fabricating a header", () => {
    const timeline = [makeVitalSignItem({ encounter_id: 99 })];
    const summaries = groupTimelineByEncounter(timeline);
    expect(summaries).toHaveLength(0);
  });

  // 최근 Encounter 먼저(백엔드 자체 정렬 규칙과 일치), tie-break는 encounter_id 내림차순.
  it("orders summaries by the most recent encounter first, deterministically", () => {
    const timeline = [
      makeEncounterItem({ id: 1, encounter_id: 1, event_time: "2026-03-01T09:00:00+00:00" }),
      makeEncounterItem({ id: 2, encounter_id: 2, event_time: "2026-03-10T09:00:00+00:00" }),
      makeEncounterItem({ id: 3, encounter_id: 3, event_time: "2026-03-05T09:00:00+00:00" }),
    ];
    const summaries = groupTimelineByEncounter(timeline);
    expect(summaries.map((s) => s.encounterItem.encounter_id)).toEqual([2, 3, 1]);
  });

  it("breaks same-timestamp ties by encounter_id descending, not input order", () => {
    const timeline = [
      makeEncounterItem({ id: 1, encounter_id: 5, event_time: "2026-03-10T09:00:00+00:00" }),
      makeEncounterItem({ id: 2, encounter_id: 7, event_time: "2026-03-10T09:00:00+00:00" }),
    ];
    const summaries = groupTimelineByEncounter(timeline);
    expect(summaries.map((s) => s.encounterItem.encounter_id)).toEqual([7, 5]);
  });

  // Within-encounter 순서는 원본 timeline 배열 순서를 그대로 보존한다(재정렬 없음).
  it("preserves the original timeline array order within a single encounter group", () => {
    const timeline = [
      makeEncounterItem({ encounter_id: 1 }),
      makeLabResultItem({ id: 202, encounter_id: 1, title: "두 번째 검사" }),
      makeLabResultItem({ id: 201, encounter_id: 1, title: "첫 번째 검사" }),
    ];
    const summaries = groupTimelineByEncounter(timeline);
    expect(summaries[0].labResults.map((item) => item.title)).toEqual(["두 번째 검사", "첫 번째 검사"]);
  });

  it("does not mutate the original timeline array", () => {
    const timeline = [makeEncounterItem(), makeVitalSignItem()];
    const snapshot = JSON.stringify(timeline);
    groupTimelineByEncounter(timeline);
    expect(JSON.stringify(timeline)).toBe(snapshot);
  });
});

describe("EncounterSummaryCard", () => {
  it("renders the encounter header from the ENCOUNTER item's own fields", () => {
    const [summary] = groupTimelineByEncounter([makeEncounterItem(), makeVitalSignItem()]);
    render(<EncounterSummaryCard summary={summary} />);

    expect(screen.getByText(/내분비내과/)).toBeInTheDocument();
    expect(screen.getByText(/내분비내과 외래 방문/)).toBeInTheDocument();
  });

  it("shows vital signs under a labeled section without any normal/abnormal judgement", () => {
    const [summary] = groupTimelineByEncounter([
      makeEncounterItem(),
      makeVitalSignItem({ title: "혈압", vital_type: "BLOOD_PRESSURE", value: "132", value_secondary: "84", unit: "mmHg" }),
    ]);
    render(<EncounterSummaryCard summary={summary} />);

    expect(screen.getByText("활력징후")).toBeInTheDocument();
    expect(screen.getByText(/혈압/)).toBeInTheDocument();
    expect(screen.getByText(/132\/84 mmHg/)).toBeInTheDocument();
    // F4-B 원칙: 정상/비정상/높음/낮음/안정적/양호 같은 판정 문구를 임의로 붙이지 않는다.
    expect(screen.queryByText(/정상|비정상|높음|낮음|안정적|양호/)).not.toBeInTheDocument();
  });

  it("shows lab results using the backend's own raw summary text, without a HIGH/LOW/NORMAL badge", () => {
    const [summary] = groupTimelineByEncounter([
      makeEncounterItem(),
      makeLabResultItem({ title: "HbA1c", summary: "7.2% (참고범위 4.0-6.0%)" }),
    ]);
    const { container } = render(<EncounterSummaryCard summary={summary} />);

    expect(screen.getByText("검사결과")).toBeInTheDocument();
    expect(screen.getByText(/HbA1c/)).toBeInTheDocument();
    expect(screen.getByText(/7\.2% \(참고범위 4\.0-6\.0%\)/)).toBeInTheDocument();
    expect(container.querySelector('[class*="badge"]')).not.toBeInTheDocument();
  });

  it("shows diagnoses using the backend's own raw code text, without labeling it as a specific code system", () => {
    const [summary] = groupTimelineByEncounter([
      makeEncounterItem(),
      makeDiagnosisItem({ title: "2형 당뇨병", summary: "진단 코드: E11.9" }),
    ]);
    render(<EncounterSummaryCard summary={summary} />);

    expect(screen.getByText("진단")).toBeInTheDocument();
    expect(screen.getByText(/2형 당뇨병/)).toBeInTheDocument();
    expect(screen.getByText(/진단 코드: E11\.9/)).toBeInTheDocument();
    expect(screen.queryByText(/KCD|ICD-10|SNOMED/)).not.toBeInTheDocument();
  });

  it("hides an empty category section instead of showing a placeholder for every card", () => {
    const [summary] = groupTimelineByEncounter([makeEncounterItem()]);
    render(<EncounterSummaryCard summary={summary} />);

    expect(screen.queryByText("활력징후")).not.toBeInTheDocument();
    expect(screen.queryByText("검사결과")).not.toBeInTheDocument();
    expect(screen.queryByText("진단")).not.toBeInTheDocument();
  });

  it("uses real heading elements for section hierarchy, not color-only differentiation", () => {
    const [summary] = groupTimelineByEncounter([makeEncounterItem(), makeVitalSignItem(), makeLabResultItem()]);
    render(<EncounterSummaryCard summary={summary} />);

    const vitalHeading = screen.getByRole("heading", { name: "활력징후" });
    const labHeading = screen.getByRole("heading", { name: "검사결과" });
    expect(vitalHeading).toBeInTheDocument();
    expect(labHeading).toBeInTheDocument();
  });

  it("does not nest an interactive report-generation button inside the card in this first iteration", () => {
    const [summary] = groupTimelineByEncounter([makeEncounterItem(), makeVitalSignItem()]);
    render(<EncounterSummaryCard summary={summary} />);

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
