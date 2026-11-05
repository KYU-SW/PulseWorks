import { describe, expect, it } from "vitest";
import { DEPARTMENT_REPORT_TEMPLATES, selectReportTemplate } from "./departmentReportTemplates";

// 1. ENDOCRINOLOGY 템플릿 선택
it("selects the ENDOCRINOLOGY template for a single endocrinology encounter", () => {
  const template = selectReportTemplate(["ENDOCRINOLOGY"]);
  expect(template.department).toBe("ENDOCRINOLOGY");
});

// 2. ORTHOPEDICS 템플릿 선택
it("selects the ORTHOPEDICS template for a single orthopedics encounter", () => {
  const template = selectReportTemplate(["ORTHOPEDICS"]);
  expect(template.department).toBe("ORTHOPEDICS");
});

// 3. EMERGENCY_MEDICINE 템플릿 선택
it("selects the EMERGENCY_MEDICINE template for a single emergency encounter", () => {
  const template = selectReportTemplate(["EMERGENCY_MEDICINE"]);
  expect(template.department).toBe("EMERGENCY_MEDICINE");
});

// 4. 진료과 없음은 DEFAULT
it("falls back to DEFAULT when there are no departments", () => {
  const template = selectReportTemplate([]);
  expect(template.department).toBe("DEFAULT");
});

// 5. 알 수 없는 진료과는 DEFAULT
it("falls back to DEFAULT for an unknown department", () => {
  const template = selectReportTemplate(["CARDIOLOGY"]);
  expect(template.department).toBe("DEFAULT");
});

// 6. 복수 진료과는 DEFAULT
it("falls back to DEFAULT when two or more distinct departments are present", () => {
  const template = selectReportTemplate(["ENDOCRINOLOGY", "ORTHOPEDICS"]);
  expect(template.department).toBe("DEFAULT");
});

// 7. 같은 진료과 반복은 해당 템플릿
it("still selects the specific template when the same department repeats", () => {
  const template = selectReportTemplate(["ENDOCRINOLOGY", "ENDOCRINOLOGY", "ENDOCRINOLOGY"]);
  expect(template.department).toBe("ENDOCRINOLOGY");
});

// 8. 각 진료과의 섹션 순서
describe("section order per department", () => {
  it("orders ENDOCRINOLOGY sections as specified", () => {
    const ids = DEPARTMENT_REPORT_TEMPLATES.ENDOCRINOLOGY.sections.map((s) => s.id);
    expect(ids).toEqual([
      "patient_info", "diagnoses", "lab_trends", "lab_results", "selected_encounter",
      "vital_signs", "prescriptions", "allergies", "safety_alerts", "clinical_notes",
      "source_record_ids",
    ]);
  });

  it("orders ORTHOPEDICS sections as specified", () => {
    const ids = DEPARTMENT_REPORT_TEMPLATES.ORTHOPEDICS.sections.map((s) => s.id);
    expect(ids).toEqual([
      "patient_info", "diagnoses", "selected_encounter", "vital_signs", "prescriptions",
      "clinical_notes", "lab_results", "allergies", "safety_alerts", "source_record_ids",
    ]);
  });

  it("orders EMERGENCY_MEDICINE sections as specified", () => {
    const ids = DEPARTMENT_REPORT_TEMPLATES.EMERGENCY_MEDICINE.sections.map((s) => s.id);
    expect(ids).toEqual([
      "patient_info", "selected_encounter", "vital_signs", "diagnoses", "lab_results",
      "prescriptions", "allergies", "safety_alerts", "clinical_notes", "source_record_ids",
    ]);
  });
});

// 9. DEFAULT 섹션 순서
it("orders DEFAULT sections as specified", () => {
  const ids = DEPARTMENT_REPORT_TEMPLATES.DEFAULT.sections.map((s) => s.id);
  expect(ids).toEqual([
    "patient_info", "selected_encounter", "vital_signs", "diagnoses", "lab_results",
    "lab_trends", "prescriptions", "allergies", "safety_alerts", "clinical_notes",
    "source_record_ids",
  ]);
});

// vitals(구 이름)/imaging_placeholder가 어떤 템플릿에도 존재하지 않음.
// "vital_signs"(Task F4-B)는 이 가드가 금지하는 대상이 아니다 — 금지된
// 것은 Task 14에서 거부된 옛 이름 "vitals"뿐이다.
it("never includes the old 'vitals' name or imaging_placeholder in any template", () => {
  for (const template of Object.values(DEPARTMENT_REPORT_TEMPLATES)) {
    const ids = template.sections.map((s) => s.id);
    expect(ids).not.toContain("vitals");
    expect(ids).not.toContain("imaging_placeholder");
  }
});
