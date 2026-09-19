import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  LabTrendPointsView,
  LabTrendPresentationPoint,
  TrendChart,
  TrendTable,
} from "./LabTrendPresentation";

const HBA1C_POINTS: LabTrendPresentationPoint[] = [
  {
    value: 7.2, unit: "%", reference_low: 4.0, reference_high: 6.0,
    measured_at: "2026-03-10T09:00:00+00:00", status: "HIGH",
    rule_id: "LAB_REFERENCE_RANGE", encounter_id: 1, source_type: "INSTITUTION_GENERATED",
  },
  {
    value: 7.8, unit: "%", reference_low: 4.0, reference_high: 6.0,
    measured_at: "2026-06-10T09:00:00+00:00", status: "HIGH",
    rule_id: "LAB_REFERENCE_RANGE", encounter_id: 2, source_type: "INSTITUTION_GENERATED",
  },
  {
    value: 8.1, unit: "%", reference_low: 4.0, reference_high: 6.0,
    measured_at: "2026-09-05T09:00:00+00:00", status: "HIGH",
    rule_id: "LAB_REFERENCE_RANGE", encounter_id: 3, source_type: "INSTITUTION_GENERATED",
  },
];

const GLUCOSE_POINTS: LabTrendPresentationPoint[] = [
  {
    value: 130, unit: "mg/dL", reference_low: 70.0, reference_high: 100.0,
    measured_at: "2026-03-10T09:00:00+00:00", status: "HIGH",
    rule_id: "LAB_REFERENCE_RANGE", encounter_id: 1, source_type: "INSTITUTION_GENERATED",
  },
  {
    value: 145, unit: "mg/dL", reference_low: 70.0, reference_high: 100.0,
    measured_at: "2026-06-10T09:00:00+00:00", status: "HIGH",
    rule_id: "LAB_REFERENCE_RANGE", encounter_id: 2, source_type: "INSTITUTION_GENERATED",
  },
];

// 값이 서로 매우 가까운 인접 점 — 라벨 겹침 회피 로직을 확인하기 위한 데이터.
const CLOSE_VALUE_POINTS: LabTrendPresentationPoint[] = [
  {
    value: 100, unit: "mg/dL", reference_low: 70.0, reference_high: 100.0,
    measured_at: "2026-01-01T09:00:00+00:00", status: "NORMAL",
    rule_id: "LAB_REFERENCE_RANGE", encounter_id: 1, source_type: "INSTITUTION_GENERATED",
  },
  {
    value: 100.5, unit: "mg/dL", reference_low: 70.0, reference_high: 100.0,
    measured_at: "2026-02-01T09:00:00+00:00", status: "HIGH",
    rule_id: "LAB_REFERENCE_RANGE", encounter_id: 2, source_type: "INSTITUTION_GENERATED",
  },
];

describe("TrendChart value labels", () => {
  it("shows every point's actual value together with its unit", () => {
    render(<TrendChart points={HBA1C_POINTS} unit="%" />);

    expect(screen.getByText("7.2%")).toBeInTheDocument();
    expect(screen.getByText("7.8%")).toBeInTheDocument();
    expect(screen.getByText("8.1%")).toBeInTheDocument();
  });

  it("shows the first and last point's value labels", () => {
    render(<TrendChart points={HBA1C_POINTS} unit="%" />);

    const first = screen.getByText("7.2%");
    const last = screen.getByText("8.1%");
    expect(first).toBeInTheDocument();
    expect(last).toBeInTheDocument();
    // 첫/마지막 라벨은 SVG 경계에서 잘리지 않도록 가운데 정렬을 쓰지 않는다.
    expect(first).toHaveAttribute("text-anchor", "start");
    expect(last).toHaveAttribute("text-anchor", "end");
  });

  it("formats an HbA1c value label with no space before the % unit", () => {
    render(<TrendChart points={HBA1C_POINTS} unit="%" />);

    expect(screen.getByText("7.2%")).toBeInTheDocument();
  });

  it("formats a Fasting Glucose value label with a space before the mg/dL unit", () => {
    render(<TrendChart points={GLUCOSE_POINTS} unit="mg/dL" />);

    expect(screen.getByText("130 mg/dL")).toBeInTheDocument();
    expect(screen.getByText("145 mg/dL")).toBeInTheDocument();
  });

  it("does not rely on color alone: every value label is real text", () => {
    render(<TrendChart points={GLUCOSE_POINTS} unit="mg/dL" />);

    const label = screen.getByText("130 mg/dL");
    expect(label.tagName.toLowerCase()).toBe("text");
    expect(label.textContent).toBe("130 mg/dL");
  });

  it("pushes a close adjacent value label further up to reduce overlap", () => {
    render(<TrendChart points={CLOSE_VALUE_POINTS} unit="mg/dL" />);

    const firstLabel = screen.getByText("100 mg/dL");
    const secondLabel = screen.getByText("100.5 mg/dL");
    const firstY = Number(firstLabel.getAttribute("y"));
    const secondY = Number(secondLabel.getAttribute("y"));
    expect(Math.abs(firstY - secondY)).toBeGreaterThanOrEqual(12);
  });

  it("never mutates the input points array or its objects", () => {
    const points = JSON.parse(JSON.stringify(HBA1C_POINTS)) as LabTrendPresentationPoint[];
    const snapshotBefore = JSON.stringify(points);

    render(<TrendChart points={points} unit="%" />);

    expect(JSON.stringify(points)).toBe(snapshotBefore);
  });
});

describe("TrendTable (no regression)", () => {
  it("still renders the raw value and unit in separate columns, unchanged", () => {
    render(<TrendTable points={GLUCOSE_POINTS} />);

    const table = screen.getByRole("table");
    expect(within(table).getByText("130")).toBeInTheDocument();
    expect(within(table).getAllByText("mg/dL").length).toBeGreaterThan(0);
    // 표에는 값과 단위를 합친 "130 mg/dL" 형태의 새 라벨이 나타나지 않는다.
    expect(within(table).queryByText("130 mg/dL")).not.toBeInTheDocument();
  });
});

describe("LabTrendPointsView single-result behavior (no regression)", () => {
  it("still renders the single-result card, not a chart, for exactly one point", () => {
    const singlePoint: LabTrendPresentationPoint[] = [
      {
        value: 118, unit: "bpm", reference_low: 60.0, reference_high: 100.0,
        measured_at: "2026-05-01T10:00:00+00:00", status: "HIGH",
        rule_id: "LAB_REFERENCE_RANGE", encounter_id: 5, source_type: "INSTITUTION_GENERATED",
      },
    ];

    render(<LabTrendPointsView points={singlePoint} unit="bpm" testName="Heart Rate" />);

    expect(screen.getByText(/측정값 1건/)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("still renders nothing for zero points", () => {
    const { container } = render(<LabTrendPointsView points={[]} unit="%" testName="HbA1c" />);

    expect(container).toBeEmptyDOMElement();
  });
});
