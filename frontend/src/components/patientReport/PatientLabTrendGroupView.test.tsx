import { render, screen } from "@testing-library/react";
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

  it("renders nothing for an empty points array", () => {
    const { container } = render(
      <PatientLabTrendGroupView group={{ test_name: "HbA1c", unit: "%", points: [] }} />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
