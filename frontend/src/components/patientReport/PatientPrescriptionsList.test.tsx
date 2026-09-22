import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PatientPrescriptionsList from "./PatientPrescriptionsList";
import { PatientPrescription } from "../../api/patientReports";

const PRESCRIPTIONS: PatientPrescription[] = [
  { medication_name: "Metformin", dosage: "500mg", prescribed_at: "2026-03-10T09:00:00Z" },
  { medication_name: "Penicillin V", dosage: "500mg", prescribed_at: "2026-09-17T14:52:27Z" },
  { medication_name: "Task10VerifyNonConflictMedX", dosage: "1 tablet", prescribed_at: "2026-09-17T14:52:27Z" },
  { medication_name: "Ibuprofen", dosage: "200mg", prescribed_at: "2026-01-01T00:00:00Z" },
];

describe("PatientPrescriptionsList", () => {
  it("shows a MedicationButton labeled 메트포르민(Metformin) for Metformin", () => {
    render(<PatientPrescriptionsList prescriptions={PRESCRIPTIONS} />);

    expect(screen.getByRole("button", { name: /메트포르민\(Metformin\)/ })).toBeInTheDocument();
  });

  it("shows a MedicationButton labeled 페니실린 V(Penicillin V) for Penicillin V", () => {
    render(<PatientPrescriptionsList prescriptions={PRESCRIPTIONS} />);

    expect(screen.getByRole("button", { name: /페니실린 V\(Penicillin V\)/ })).toBeInTheDocument();
  });

  it("formats 500mg as 500 mg", () => {
    render(<PatientPrescriptionsList prescriptions={PRESCRIPTIONS} />);

    expect(screen.getAllByText(/500 mg/).length).toBeGreaterThan(0);
    expect(screen.queryByText("500mg")).not.toBeInTheDocument();
  });

  it("formats 1 tablet as 1정", () => {
    render(<PatientPrescriptionsList prescriptions={PRESCRIPTIONS} />);

    expect(screen.getByText(/1정/)).toBeInTheDocument();
  });

  it("shows the development-only test medication as a transparent notice, with no explanation button", () => {
    render(<PatientPrescriptionsList prescriptions={PRESCRIPTIONS} />);

    expect(screen.getByText("합성 테스트 약물(개발 검증용)")).toBeInTheDocument();
    expect(screen.queryByText("Task10VerifyNonConflictMedX")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Task10VerifyNonConflictMedX/ })
    ).not.toBeInTheDocument();
  });

  it("shows an unregistered medication as plain text with no button and no console warning", () => {
    const warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    render(<PatientPrescriptionsList prescriptions={PRESCRIPTIONS} />);

    expect(screen.getByText(/Ibuprofen/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Ibuprofen/ })).not.toBeInTheDocument();
    expect(warnSpy).not.toHaveBeenCalled();
    warnSpy.mockRestore();
  });

  it("never mutates the input prescriptions array or its objects", () => {
    const snapshotBefore = JSON.stringify(PRESCRIPTIONS);

    render(<PatientPrescriptionsList prescriptions={PRESCRIPTIONS} />);

    expect(JSON.stringify(PRESCRIPTIONS)).toBe(snapshotBefore);
  });

  it("renders nothing for an empty list", () => {
    const { container } = render(<PatientPrescriptionsList prescriptions={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  // Task 20C: 각 처방을 ul/li 유지 + li 안에 Card로 감싸고, 용량과
  // 처방일을 별도 문단으로 분리했다.
  it("wraps each prescription in a Card inside the existing ul/li structure", () => {
    const { container } = render(<PatientPrescriptionsList prescriptions={PRESCRIPTIONS} />);
    const list = container.querySelector("ul");
    expect(list).not.toBeNull();
    expect(container.querySelectorAll("li .ui-card")).toHaveLength(PRESCRIPTIONS.length);
  });

  it("shows dosage and prescribed date as separate lines", () => {
    render(<PatientPrescriptionsList prescriptions={PRESCRIPTIONS} />);
    expect(screen.getAllByText(/용량: 500 mg/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/처방일: /).length).toBe(PRESCRIPTIONS.length);
  });
});
