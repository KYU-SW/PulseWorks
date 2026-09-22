import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import PatientLabTrendGroupView from "./PatientLabTrendGroupView";
import { PatientLabTrendGroup } from "../../api/patientReports";

const SINGLE_POINT_GROUP: PatientLabTrendGroup = {
  test_name: "Heart Rate",
  unit: "bpm",
  points: [
    { value: 118, unit: "bpm", reference_low: 60.0, reference_high: 100.0, measured_at: "2026-05-01T10:00:00Z", status: "HIGH" },
  ],
};

const MULTI_POINT_GROUP: PatientLabTrendGroup = {
  test_name: "HbA1c",
  unit: "%",
  points: [
    { value: 7.2, unit: "%", reference_low: 4.0, reference_high: 6.0, measured_at: "2026-03-10T09:00:00Z", status: "HIGH" },
    { value: 7.8, unit: "%", reference_low: 4.0, reference_high: 6.0, measured_at: "2026-06-10T09:00:00Z", status: "HIGH" },
  ],
};

describe("PatientLabTrendGroupView", () => {
  it("shows the single-result card for exactly one point", () => {
    render(<PatientLabTrendGroupView group={SINGLE_POINT_GROUP} />);
    expect(screen.getByText(/측정값 1건/)).toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("shows the trend chart (role=img) for two or more points", () => {
    render(<PatientLabTrendGroupView group={MULTI_POINT_GROUP} />);
    expect(screen.getByRole("img", { name: /검사값 추세 그래프/ })).toBeInTheDocument();
  });

  it("shows a MedicalTermButton for the registered test name (HbA1c)", () => {
    render(<PatientLabTrendGroupView group={MULTI_POINT_GROUP} />);
    expect(screen.getByRole("button", { name: /HbA1c/ })).toBeInTheDocument();
  });

  it("keeps the value and unit strings unchanged", () => {
    render(<PatientLabTrendGroupView group={MULTI_POINT_GROUP} />);
    expect(screen.getByText("7.2%")).toBeInTheDocument();
  });

  it("wraps the chart/card area in the shared Card component", () => {
    const { container } = render(<PatientLabTrendGroupView group={MULTI_POINT_GROUP} />);
    expect(container.querySelector(".ui-card")).not.toBeNull();
  });

  // 재현: h3(제목)는 phrasing content만 허용하는데, MedicalTermButton이
  // 열릴 때 형제로 렌더링하는 <dialog>(flow content)가 지금은 h3 안에
  // 그대로 들어간다 — 이 테스트로 그 실제 DOM 구조를 먼저 확인한다.
  it("never renders the native dialog as a descendant of the h3 heading", async () => {
    render(<PatientLabTrendGroupView group={MULTI_POINT_GROUP} />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: /HbA1c/ }));

    const dialog = screen.getByRole("dialog", { hidden: true });
    const heading = screen.getByRole("heading", { level: 3 });
    expect(heading.contains(dialog)).toBe(false);
  });

  it("renders nothing for an empty points array", () => {
    const { container } = render(
      <PatientLabTrendGroupView group={{ test_name: "HbA1c", unit: "%", points: [] }} />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
