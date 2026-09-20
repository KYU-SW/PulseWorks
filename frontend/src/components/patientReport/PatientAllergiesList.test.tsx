import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PatientAllergiesList from "./PatientAllergiesList";
import { PatientAllergy } from "../../api/patientReports";

const ALLERGIES: PatientAllergy[] = [
  { substance: "Penicillin", reaction: "두드러기", severity: "MODERATE" },
  { substance: "Latex", reaction: "발진", severity: "WEIRD_UNRECOGNIZED_VALUE" },
];

describe("PatientAllergiesList", () => {
  it("shows the substance", () => {
    render(<PatientAllergiesList allergies={ALLERGIES} />);
    expect(screen.getByText(/Penicillin/)).toBeInTheDocument();
  });

  it("shows the recorded reaction", () => {
    render(<PatientAllergiesList allergies={ALLERGIES} />);
    expect(screen.getByText(/두드러기/)).toBeInTheDocument();
  });

  it("shows MODERATE as 중간", () => {
    render(<PatientAllergiesList allergies={ALLERGIES} />);
    expect(screen.getByText(/중간/)).toBeInTheDocument();
  });

  it("shows an unrecognized severity as 확인 필요, without leaking the raw internal value", () => {
    render(<PatientAllergiesList allergies={ALLERGIES} />);
    expect(screen.getByText(/확인 필요/)).toBeInTheDocument();
    expect(screen.queryByText(/WEIRD_UNRECOGNIZED_VALUE/)).not.toBeInTheDocument();
  });

  it("never mutates the input allergies array or its objects", () => {
    const snapshotBefore = JSON.stringify(ALLERGIES);

    render(<PatientAllergiesList allergies={ALLERGIES} />);

    expect(JSON.stringify(ALLERGIES)).toBe(snapshotBefore);
  });

  it("renders nothing for an empty list", () => {
    const { container } = render(<PatientAllergiesList allergies={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
