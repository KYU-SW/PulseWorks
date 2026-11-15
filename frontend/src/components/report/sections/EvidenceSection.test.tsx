import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import {
  EmrSnapshot,
  SnapshotDiagnosis,
  SnapshotLabResult,
  SnapshotVitalSign,
} from "../../../api/clinicalReports";
import EvidenceSection from "./EvidenceSection";

// UX-1D: Evidence Viewer의 유일한 source는 emr_snapshot의 구조화
// 데이터(vital_signs/lab_results/diagnoses)다. 이 파일은 fetch/API/
// narrative_providers/evidence_tags를 전혀 import하지 않는다 - AI
// self-report 경로가 구조적으로 존재하지 않음을 보장한다.

function makeVitalSign(overrides: Partial<SnapshotVitalSign> = {}): SnapshotVitalSign {
  return {
    id: 1,
    encounter_id: 1,
    vital_type: "BLOOD_PRESSURE",
    value: "132",
    value_secondary: "84",
    unit: "mmHg",
    measured_at: "2026-03-10T09:00:00Z",
    ...overrides,
  };
}

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

function makeDiagnosis(overrides: Partial<SnapshotDiagnosis> = {}): SnapshotDiagnosis {
  return {
    id: 1,
    encounter_id: 1,
    code: "E11.9",
    description: "2형 당뇨병",
    diagnosed_at: "2026-03-10T09:00:00Z",
    source_type: "INSTITUTION_GENERATED",
    ...overrides,
  };
}

function makeSnapshot(overrides: Partial<EmrSnapshot> = {}): EmrSnapshot {
  return {
    patient: { id: 1, mrn: "SYN-0001", name: "합성환자-내분비01", birth_date: "1968-04-12" },
    encounters: [],
    diagnoses: [],
    lab_results: [],
    lab_trends: [],
    prescriptions: [],
    allergies: [],
    safety_alerts: [],
    clinical_notes: [],
    vital_signs: [],
    source_record_ids: [],
    ...overrides,
  };
}

describe("EvidenceSection internal identifier hiding", () => {
  it("never renders the raw source_record_ids values even when present on the snapshot", () => {
    render(
      <EvidenceSection
        snapshot={makeSnapshot({
          source_record_ids: ["vital_sign:123", "lab_result:456", "diagnosis:789"],
          vital_signs: [makeVitalSign({ id: 123 })],
          lab_results: [makeLabResult({ id: 456 })],
          diagnoses: [makeDiagnosis({ id: 789 })],
        })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.queryByText(/vital_sign:123/)).not.toBeInTheDocument();
    expect(screen.queryByText(/lab_result:456/)).not.toBeInTheDocument();
    expect(screen.queryByText(/diagnosis:789/)).not.toBeInTheDocument();
  });

  it("never renders internal evidence-tag prefixes or bare numeric record ids", () => {
    const { container } = render(
      <EvidenceSection
        snapshot={makeSnapshot({
          vital_signs: [makeVitalSign({ id: 123 })],
          lab_results: [makeLabResult({ id: 456 })],
          diagnoses: [makeDiagnosis({ id: 789 })],
        })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.queryByText(/\bV1\b|\bE1\b|\bD1\b|\bL1\b|\bP1\b|\bA1\b/)).not.toBeInTheDocument();
    // DOM 어디에도 숫자 id(123/456/789)가 '보이는 텍스트'로 노출되지 않는다.
    // (React key로 쓰이는 것은 접근성 트리/텍스트 콘텐츠에 나타나지 않는다.)
    expect(container.textContent).not.toMatch(/123|456|789/);
  });

  it("still shows the user-readable clinical evidence while internal ids stay hidden", () => {
    render(
      <EvidenceSection
        snapshot={makeSnapshot({
          source_record_ids: ["vital_sign:123", "lab_result:456", "diagnosis:789"],
          vital_signs: [makeVitalSign()],
          lab_results: [makeLabResult()],
          diagnoses: [makeDiagnosis()],
        })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.getByText(/132\/84 mmHg/)).toBeInTheDocument();
    expect(screen.getByText(/HbA1c/)).toBeInTheDocument();
    expect(screen.getByText(/2형 당뇨병/)).toBeInTheDocument();
    expect(screen.queryByText(/vital_sign:123/)).not.toBeInTheDocument();
  });

  it("shows clinical evidence even when source_record_ids is empty (display never depends on it)", () => {
    render(
      <EvidenceSection
        snapshot={makeSnapshot({
          source_record_ids: [],
          vital_signs: [makeVitalSign()],
        })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.getByText(/132\/84 mmHg/)).toBeInTheDocument();
  });
});

describe("EvidenceSection vital sign evidence", () => {
  it("shows the Korean vital label, blood pressure primary/secondary values, and unit", () => {
    render(
      <EvidenceSection
        snapshot={makeSnapshot({ vital_signs: [makeVitalSign({ value: "132", value_secondary: "84", unit: "mmHg" })] })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.getByText("활력징후")).toBeInTheDocument();
    expect(screen.getByText(/혈압/)).toBeInTheDocument();
    expect(screen.getByText(/132\/84 mmHg/)).toBeInTheDocument();
  });

  it("never adds a normal/abnormal judgement word to vital sign evidence", () => {
    render(
      <EvidenceSection
        snapshot={makeSnapshot({ vital_signs: [makeVitalSign()] })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.queryByText(/정상|비정상|높음|낮음|안정적|양호|위험/)).not.toBeInTheDocument();
  });
});

describe("EvidenceSection lab result evidence", () => {
  it("shows the test name, value, unit, and reference range", () => {
    render(
      <EvidenceSection
        snapshot={makeSnapshot({
          lab_results: [makeLabResult({ test_name: "HbA1c", value: 7.2, unit: "%", reference_low: 4.0, reference_high: 6.0 })],
        })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.getByText("검사결과")).toBeInTheDocument();
    expect(screen.getByText(/HbA1c/)).toBeInTheDocument();
    expect(screen.getByText(/7\.2%/)).toBeInTheDocument();
    expect(screen.getByText(/4-6%/)).toBeInTheDocument();
  });
});

describe("EvidenceSection diagnosis evidence", () => {
  it("shows the diagnosis description and raw code", () => {
    render(
      <EvidenceSection
        snapshot={makeSnapshot({ diagnoses: [makeDiagnosis({ description: "2형 당뇨병", code: "E11.9" })] })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.getByText("진단")).toBeInTheDocument();
    expect(screen.getByText(/2형 당뇨병/)).toBeInTheDocument();
    expect(screen.getByText(/E11\.9/)).toBeInTheDocument();
  });

  it("never labels the diagnosis code as a specific code system", () => {
    render(
      <EvidenceSection
        snapshot={makeSnapshot({ diagnoses: [makeDiagnosis()] })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.queryByText(/KCD|ICD-10|SNOMED/)).not.toBeInTheDocument();
  });
});

describe("EvidenceSection empty categories", () => {
  it("hides a category heading when that category has no data", () => {
    render(
      <EvidenceSection
        snapshot={makeSnapshot({ vital_signs: [makeVitalSign()] })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );

    expect(screen.getByText("활력징후")).toBeInTheDocument();
    expect(screen.queryByText("검사결과")).not.toBeInTheDocument();
    expect(screen.queryByText("진단")).not.toBeInTheDocument();
  });

  it("renders nothing when every evidence category is empty, regardless of source_record_ids", () => {
    const { container } = render(
      <EvidenceSection
        snapshot={makeSnapshot({ source_record_ids: ["encounter:1"] })}
        title="근거 기록"
        emptyBehavior="hide"
      />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
