import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PatientVitalSignsList from "./PatientVitalSignsList";
import { PatientVitalSign } from "../../api/patientReports";

const VITAL_SIGNS: PatientVitalSign[] = [
  {
    vital_type: "BLOOD_PRESSURE", value: "120.000", value_secondary: "80.000",
    unit: "mmHg", measured_at: "2026-03-10T09:00:00Z",
  },
  {
    vital_type: "BODY_TEMPERATURE", value: "36.500", value_secondary: null,
    unit: "Cel", measured_at: "2026-03-10T09:00:00Z",
  },
];

describe("PatientVitalSignsList", () => {
  it("shows the Korean label for each vital type", () => {
    render(<PatientVitalSignsList vitalSigns={VITAL_SIGNS} />);
    expect(screen.getByText(/혈압/)).toBeInTheDocument();
    expect(screen.getByText(/체온/)).toBeInTheDocument();
  });

  it("shows blood pressure as systolic/diastolic with the display unit", () => {
    render(<PatientVitalSignsList vitalSigns={VITAL_SIGNS} />);
    expect(screen.getByText(/120\/80\s*mmHg/)).toBeInTheDocument();
  });

  it("shows body temperature with the Celsius display label, not the canonical code", () => {
    render(<PatientVitalSignsList vitalSigns={VITAL_SIGNS} />);
    expect(screen.getByText(/36\.5\s*℃/)).toBeInTheDocument();
    expect(screen.queryByText(/Cel\b/)).not.toBeInTheDocument();
  });

  it("never renders internal fields such as vital_type raw strings, ids, or quality warnings", () => {
    const { container } = render(<PatientVitalSignsList vitalSigns={VITAL_SIGNS} />);
    const text = container.textContent ?? "";
    expect(text).not.toContain("BLOOD_PRESSURE");
    expect(text).not.toContain("BODY_TEMPERATURE");
  });

  it("never mutates the input array or its objects", () => {
    const snapshotBefore = JSON.stringify(VITAL_SIGNS);
    render(<PatientVitalSignsList vitalSigns={VITAL_SIGNS} />);
    expect(JSON.stringify(VITAL_SIGNS)).toBe(snapshotBefore);
  });

  it("renders nothing for an empty list", () => {
    const { container } = render(<PatientVitalSignsList vitalSigns={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
