import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { EmrSnapshot, SnapshotLabResult } from "../../../api/clinicalReports";
import LabResultsTableSection from "./LabResultsTableSection";

// UX-1C: status의 source는 오직 SnapshotLabResult.status(구조화된
// Backend 값)다 - 이 파일은 fetch/API/narrative/provider를 전혀 import하지
// 않는다. AI가 이 판정을 만들지 않는다는 사실을 구조적으로 보장한다.

function makeLabResult(overrides: Partial<SnapshotLabResult> = {}): SnapshotLabResult {
  return {
    id: 1,
    encounter_id: 1,
    test_name: "HbA1c",
    value: 7.2,
    unit: "%",
    reference_low: 4.0,
    reference_high: 6.0,
    measured_at: "2026-03-10T09:00:00Z",
    source_type: "INSTITUTION_GENERATED",
    status: "HIGH",
    rule_id: "LAB_REFERENCE_RANGE",
    ...overrides,
  };
}

function makeSnapshot(labResults: SnapshotLabResult[]): EmrSnapshot {
  return {
    patient: { id: 1, mrn: "SYN-0001", name: "합성환자-내분비01", birth_date: "1968-04-12" },
    encounters: [],
    diagnoses: [],
    lab_results: labResults,
    lab_trends: [],
    prescriptions: [],
    allergies: [],
    safety_alerts: [],
    clinical_notes: [],
    vital_signs: [],
    source_record_ids: [],
  };
}

describe("LabResultsTableSection status badge", () => {
  it.each([
    ["HIGH", "높음"],
    ["LOW", "낮음"],
    ["NORMAL", "정상"],
    ["UNKNOWN", "판정불가"],
  ])("shows the existing official label for status=%s", (status, label) => {
    render(
      <LabResultsTableSection
        snapshot={makeSnapshot([makeLabResult({ status })])}
        title="검사결과"
        emptyBehavior="hide"
      />
    );
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("falls back to a safe label instead of leaking an unrecognized raw status value", () => {
    render(
      <LabResultsTableSection
        snapshot={makeSnapshot([makeLabResult({ status: "WEIRD_RAW_CODE" })])}
        title="검사결과"
        emptyBehavior="hide"
      />
    );
    expect(screen.queryByText("WEIRD_RAW_CODE")).not.toBeInTheDocument();
  });

  it("renders the status using the shared color-class badge, not a bare text cell", () => {
    const { container } = render(
      <LabResultsTableSection
        snapshot={makeSnapshot([makeLabResult({ status: "HIGH" })])}
        title="검사결과"
        emptyBehavior="hide"
      />
    );
    expect(container.querySelector(".ui-status-badge--lab-high")).toBeInTheDocument();
    // 색상 class와 별개로 text label이 항상 존재한다(색상 단독 전달 금지).
    expect(screen.getByText("높음")).toBeVisible();
  });
});

describe("LabResultsTableSection out-of-range filter", () => {
  function allStatusesSnapshot(): EmrSnapshot {
    return makeSnapshot([
      makeLabResult({ id: 1, test_name: "검사-LOW", status: "LOW" }),
      makeLabResult({ id: 2, test_name: "검사-NORMAL", status: "NORMAL" }),
      makeLabResult({ id: 3, test_name: "검사-HIGH", status: "HIGH" }),
      makeLabResult({ id: 4, test_name: "검사-UNKNOWN", status: "UNKNOWN" }),
    ]);
  }

  it("shows every status by default (전체)", () => {
    render(<LabResultsTableSection snapshot={allStatusesSnapshot()} title="검사결과" emptyBehavior="hide" />);

    expect(screen.getByText("검사-LOW")).toBeInTheDocument();
    expect(screen.getByText("검사-NORMAL")).toBeInTheDocument();
    expect(screen.getByText("검사-HIGH")).toBeInTheDocument();
    expect(screen.getByText("검사-UNKNOWN")).toBeInTheDocument();
  });

  it("shows only HIGH and LOW results when the out-of-range filter is checked", async () => {
    render(<LabResultsTableSection snapshot={allStatusesSnapshot()} title="검사결과" emptyBehavior="hide" />);
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("참고범위 밖만 보기"));

    expect(screen.getByText("검사-LOW")).toBeInTheDocument();
    expect(screen.getByText("검사-HIGH")).toBeInTheDocument();
    expect(screen.queryByText("검사-NORMAL")).not.toBeInTheDocument();
    expect(screen.queryByText("검사-UNKNOWN")).not.toBeInTheDocument();
  });

  it("shows every status again after unchecking the filter", async () => {
    render(<LabResultsTableSection snapshot={allStatusesSnapshot()} title="검사결과" emptyBehavior="hide" />);
    const user = userEvent.setup();
    const checkbox = screen.getByLabelText("참고범위 밖만 보기");

    await user.click(checkbox);
    await user.click(checkbox);

    expect(screen.getByText("검사-NORMAL")).toBeInTheDocument();
    expect(screen.getByText("검사-UNKNOWN")).toBeInTheDocument();
  });

  it("does not mutate the original snapshot.lab_results array when filtering", async () => {
    const snapshot = allStatusesSnapshot();
    const originalOrder = snapshot.lab_results.map((lab) => lab.id);
    render(<LabResultsTableSection snapshot={snapshot} title="검사결과" emptyBehavior="hide" />);
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("참고범위 밖만 보기"));

    expect(snapshot.lab_results.map((lab) => lab.id)).toEqual(originalOrder);
    expect(snapshot.lab_results).toHaveLength(4);
  });

  it("shows a filter-specific empty message when no result is out of range, distinct from the no-data message", async () => {
    const snapshot = makeSnapshot([makeLabResult({ status: "NORMAL" }), makeLabResult({ id: 2, status: "UNKNOWN" })]);
    render(<LabResultsTableSection snapshot={snapshot} title="검사결과" emptyBehavior="hide" />);
    const user = userEvent.setup();

    await user.click(screen.getByLabelText("참고범위 밖만 보기"));

    expect(screen.getByText("참고범위를 벗어난 검사결과가 없습니다.")).toBeInTheDocument();
    expect(screen.queryByText("검사결과가 없습니다.")).not.toBeInTheDocument();
  });

  it("still hides the whole section when there are no lab results at all (unchanged regression)", () => {
    const { container } = render(
      <LabResultsTableSection snapshot={makeSnapshot([])} title="검사결과" emptyBehavior="hide" />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("keeps the existing reference range display unchanged", () => {
    render(
      <LabResultsTableSection
        snapshot={makeSnapshot([makeLabResult({ reference_low: 4.0, reference_high: 6.0, unit: "%" })])}
        title="검사결과"
        emptyBehavior="hide"
      />
    );
    expect(screen.getByText("4-6%")).toBeInTheDocument();
  });

  it("labels the filter checkbox with real, keyboard-accessible text, not placeholder-only", () => {
    render(<LabResultsTableSection snapshot={allStatusesSnapshot()} title="검사결과" emptyBehavior="hide" />);
    const checkbox = screen.getByLabelText("참고범위 밖만 보기");
    expect(checkbox).toHaveAttribute("type", "checkbox");
    expect(checkbox).not.toBeChecked();
  });
});
