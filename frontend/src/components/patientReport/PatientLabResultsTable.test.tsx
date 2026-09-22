import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PatientLabResultsTable from "./PatientLabResultsTable";
import { PatientLabResult } from "../../api/patientReports";

const LAB_RESULTS: PatientLabResult[] = [
  {
    test_name: "HbA1c", value: 7.2, unit: "%", reference_low: 4.0, reference_high: 6.0,
    measured_at: "2026-03-10T09:00:00Z", status: "HIGH",
  },
  {
    test_name: "알 수 없는 검사", value: 1, unit: "unit", reference_low: 0, reference_high: 2,
    measured_at: "2026-03-10T09:00:00Z", status: "NORMAL",
  },
];

describe("PatientLabResultsTable", () => {
  it("preserves the table role and th scope", () => {
    render(<PatientLabResultsTable labResults={LAB_RESULTS} />);

    const table = screen.getByRole("table");
    expect(table).toBeInTheDocument();
    expect(within(table).getAllByRole("columnheader")).toHaveLength(5);
    expect(within(table).getByRole("columnheader", { name: "검사명" })).toHaveAttribute(
      "scope",
      "col"
    );
  });

  it("wraps the table in the shared DataTable scroll wrapper", () => {
    const { container } = render(<PatientLabResultsTable labResults={LAB_RESULTS} />);
    expect(container.firstElementChild?.className).toContain("ui-table-scroll");
  });

  it("shows a MedicalTermButton for a registered test name (HbA1c)", () => {
    render(<PatientLabResultsTable labResults={LAB_RESULTS} />);
    expect(screen.getByRole("button", { name: /HbA1c/ })).toBeInTheDocument();
  });

  it("shows an unregistered test name as plain text, not a button", () => {
    render(<PatientLabResultsTable labResults={LAB_RESULTS} />);
    expect(screen.getByText("알 수 없는 검사")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /알 수 없는 검사/ })).not.toBeInTheDocument();
  });

  it("keeps the value and unit strings unchanged", () => {
    render(<PatientLabResultsTable labResults={LAB_RESULTS} />);
    expect(screen.getByText("7.2%")).toBeInTheDocument();
  });

  it("renders nothing for an empty list", () => {
    const { container } = render(<PatientLabResultsTable labResults={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
