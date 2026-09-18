import { render, screen, within } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ReportContentSnapshot } from "../../api/clinicalReports";
import ReportRenderer from "./ReportRenderer";

function baseSnapshot(overrides: Partial<ReportContentSnapshot["emr_snapshot"]> = {}) {
  return {
    patient: { id: 1, mrn: "SYN-0001", name: "합성환자-내분비01", birth_date: "1968-04-12" },
    encounters: [
      {
        id: 1, department: "ENDOCRINOLOGY", encounter_type: "OUTPATIENT",
        start_time: "2026-03-10T09:00:00Z", end_time: null,
      },
    ],
    diagnoses: [
      {
        id: 1, encounter_id: 1, code: "E11.9", description: "2형 당뇨병 신규 진단 (합성 데이터)",
        diagnosed_at: "2026-03-10T09:00:00Z", source_type: "INSTITUTION_GENERATED",
      },
    ],
    lab_results: [
      {
        id: 1, encounter_id: 1, test_name: "HbA1c", value: 7.2, unit: "%",
        reference_low: 4.0, reference_high: 6.0, measured_at: "2026-03-10T09:00:00Z",
        source_type: "INSTITUTION_GENERATED", status: "HIGH", rule_id: "LAB_REFERENCE_RANGE",
      },
    ],
    lab_trends: [
      {
        test_name: "HbA1c", unit: "%",
        points: [
          {
            value: 7.2, unit: "%", reference_low: 4.0, reference_high: 6.0,
            measured_at: "2026-03-10T09:00:00Z", status: "HIGH", rule_id: "LAB_REFERENCE_RANGE",
            encounter_id: 1, source_type: "INSTITUTION_GENERATED",
          },
        ],
      },
    ],
    prescriptions: [
      {
        id: 1, encounter_id: 1, medication_name: "Metformin", dosage: "500mg",
        prescribed_by_user_id: 1, prescribed_at: "2026-03-10T09:00:00Z",
        source_type: "INSTITUTION_GENERATED",
      },
    ],
    allergies: [
      {
        id: 1, substance: "Penicillin", reaction: "두드러기 (합성 데이터)", severity: "MODERATE",
        recorded_at: "2026-01-01T09:00:00Z", source_type: "INSTITUTION_GENERATED",
      },
    ],
    safety_alerts: [
      {
        id: 1, encounter_id: 1, prescription_id: 5, lab_result_id: null,
        rule_id: "ALLERGY_MEDICATION_CONFLICT", priority: "HIGH",
        evidence: { explanation: "테스트 설명문" }, created_at: "2026-09-17T14:52:27Z",
      },
    ],
    clinical_notes: [
      {
        id: 1, encounter_id: 1, author_user_id: 1, preview_text: "합성 진료기록 미리보기",
        created_at: "2026-03-10T09:00:00Z", source_type: "INSTITUTION_GENERATED",
      },
    ],
    source_record_ids: ["encounter:1", "diagnosis:1"],
    ...overrides,
  };
}

function contentFor(overrides: Partial<ReportContentSnapshot["emr_snapshot"]> = {}): ReportContentSnapshot {
  return {
    emr_snapshot: baseSnapshot(overrides),
    narrative: null,
    handoff_note: null,
    patient_guidance: null,
  };
}

function headingTexts(): string[] {
  return screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent ?? "");
}

// 10. patient_info 항상 표시 & 11. selected_encounter 항상 표시
it("always shows patient_info and selected_encounter", () => {
  render(<ReportRenderer content={contentFor()} />);
  expect(screen.getByText(/합성환자-내분비01/)).toBeInTheDocument();
  expect(screen.getByText(/내분비내과 외래/)).toBeInTheDocument();
});

// 8. ENDOCRINOLOGY 섹션 순서
it("orders ENDOCRINOLOGY report sections as specified", () => {
  render(<ReportRenderer content={contentFor()} />);
  expect(headingTexts()).toEqual([
    "환자 기본정보", "주요 진단", "검사 추세", "검사결과", "선택 Encounter",
    "처방 기록", "알레르기", "안전 알림", "진료기록 미리보기", "근거 기록",
  ]);
});

// 8. ORTHOPEDICS 섹션 순서
it("orders ORTHOPEDICS report sections as specified", () => {
  const content = contentFor({
    encounters: [
      { id: 2, department: "ORTHOPEDICS", encounter_type: "OUTPATIENT", start_time: "2026-01-01T00:00:00Z", end_time: null },
    ],
  });
  render(<ReportRenderer content={content} />);
  expect(headingTexts()).toEqual([
    "환자 기본정보", "주요 진단", "선택 Encounter", "처방 기록", "진료기록 미리보기",
    "검사결과", "알레르기", "안전 알림", "근거 기록",
  ]);
});

// 8. EMERGENCY_MEDICINE 섹션 순서
it("orders EMERGENCY_MEDICINE report sections as specified", () => {
  const content = contentFor({
    encounters: [
      { id: 3, department: "EMERGENCY_MEDICINE", encounter_type: "EMERGENCY", start_time: "2026-01-01T00:00:00Z", end_time: null },
    ],
  });
  render(<ReportRenderer content={content} />);
  expect(headingTexts()).toEqual([
    "환자 기본정보", "선택 Encounter", "주요 진단", "검사결과", "처방 기록",
    "알레르기", "안전 알림", "진료기록 미리보기", "근거 기록",
  ]);
});

// 9. DEFAULT 섹션 순서 (알 수 없는 진료과)
it("orders DEFAULT report sections for an unknown department", () => {
  const content = contentFor({
    encounters: [
      { id: 4, department: "CARDIOLOGY", encounter_type: "OUTPATIENT", start_time: "2026-01-01T00:00:00Z", end_time: null },
    ],
  });
  render(<ReportRenderer content={content} />);
  expect(headingTexts()).toEqual([
    "환자 기본정보", "선택 Encounter", "주요 진단", "검사결과", "검사 추세",
    "처방 기록", "알레르기", "안전 알림", "진료기록 미리보기", "근거 기록",
  ]);
});

// 12. allergies 빈 상태 표시 & 13. safety_alerts 빈 상태 표시
it("shows a factual empty state for allergies and safety_alerts when empty", () => {
  const content = contentFor({ allergies: [], safety_alerts: [] });
  render(<ReportRenderer content={content} />);
  expect(screen.getByText("등록된 합성 알레르기 정보가 없습니다.")).toBeInTheDocument();
  expect(screen.getByText("표시할 안전 알림이 없습니다.")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "알레르기" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "안전 알림" })).toBeInTheDocument();
});

// 14~19. 비면 숨김: diagnoses/lab_trends/lab_results/prescriptions/clinical_notes/source_record_ids
it("hides diagnoses, lab_trends, lab_results, prescriptions, clinical_notes, and source_record_ids when empty", () => {
  const content = contentFor({
    diagnoses: [], lab_trends: [], lab_results: [], prescriptions: [],
    clinical_notes: [], source_record_ids: [],
  });
  render(<ReportRenderer content={content} />);
  const headings = headingTexts();
  for (const hidden of ["주요 진단", "검사 추세", "검사결과", "처방 기록", "진료기록 미리보기", "근거 기록"]) {
    expect(headings).not.toContain(hidden);
  }
  // 항상 표시되는 섹션은 그대로 남아 있어야 한다
  expect(headings).toContain("환자 기본정보");
  expect(headings).toContain("선택 Encounter");
});

// 20. 보고서 검사 추세가 스냅샷만으로 렌더링 & 21. 추가 fetch 없음
it("renders lab trends from the snapshot alone without calling fetch", () => {
  const fetchSpy = vi.fn();
  vi.stubGlobal("fetch", fetchSpy);

  render(<ReportRenderer content={contentFor()} />);

  expect(screen.getByText(/HbA1c \(%\)/)).toBeInTheDocument();
  expect(screen.getByText(/측정값 1건/)).toBeInTheDocument(); // 단일 결과 카드
  expect(fetchSpy).not.toHaveBeenCalled();

  vi.unstubAllGlobals();
});

// 22. 원본 content 객체 변경 없음
it("never mutates the input content object", () => {
  const content = contentFor();
  const before = JSON.parse(JSON.stringify(content));

  render(<ReportRenderer content={content} />);

  expect(content).toEqual(before);
});

// 23. 영상 img 요소 없음 & 24. vitals 섹션 없음
it("never renders an img element and never renders a vitals section", () => {
  render(<ReportRenderer content={contentFor()} />);
  expect(screen.queryByRole("img")).not.toBeInTheDocument(); // svg role="img"도 없어야 함(lab_trends 그래프는 2점 이상일 때만 등장)
  expect(headingTexts()).not.toContain("활력징후");
});

// 25. 섹션 heading과 aria-labelledby 연결
it("connects each section to its heading via aria-labelledby", () => {
  render(<ReportRenderer content={contentFor()} />);
  const patientSection = screen.getByRole("region", { name: "환자 기본정보" });
  expect(within(patientSection).getByRole("heading", { name: "환자 기본정보" })).toBeInTheDocument();
});

// 26. 표의 th scope 확인
it("uses th scope=col in the lab results table", () => {
  render(<ReportRenderer content={contentFor()} />);
  const table = screen.getAllByRole("table")[0];
  const headerCell = within(table).getAllByRole("columnheader")[0];
  expect(headerCell).toHaveAttribute("scope", "col");
});

// 27. LOW, NORMAL, HIGH, UNKNOWN 텍스트 표시
it("shows lab status as Korean text, not only a raw enum value", () => {
  render(<ReportRenderer content={contentFor()} />);
  expect(screen.getAllByText("높음").length).toBeGreaterThan(0); // HIGH -> 높음
});
