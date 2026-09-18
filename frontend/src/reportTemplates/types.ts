// Task 14 보고서 섹션 템플릿 타입. 이 10개로 제한한다 — vitals와
// imaging_placeholder는 만들지 않는다(구조화된 활력징후 데이터/실제
// 합성 이미지가 없는 상태에서 test_name 하드코딩 분류나 가짜 영상
// placeholder를 보고서에 넣지 않기 위함, 향후 별도 Task에서 추가 가능).
export type ReportSectionId =
  | "patient_info"
  | "selected_encounter"
  | "diagnoses"
  | "lab_trends"
  | "lab_results"
  | "prescriptions"
  | "allergies"
  | "safety_alerts"
  | "clinical_notes"
  | "source_record_ids";

export type ReportSectionEmptyBehavior = "hide" | "show_empty_state";

export type ReportSectionConfig = {
  id: ReportSectionId;
  title: string;
  emptyBehavior: ReportSectionEmptyBehavior;
};

export type ReportDepartment =
  | "ENDOCRINOLOGY"
  | "ORTHOPEDICS"
  | "EMERGENCY_MEDICINE"
  | "DEFAULT";

export type DepartmentReportTemplate = {
  department: ReportDepartment;
  sections: ReportSectionConfig[];
};
