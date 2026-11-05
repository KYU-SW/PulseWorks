// Task 14 보고서 섹션 템플릿 타입. imaging_placeholder는 만들지 않는다
// (실제 합성 이미지가 없는 상태에서 가짜 영상 placeholder를 보고서에
// 넣지 않기 위함). Task F4-B: EmrSnapshot에 구조화된 VitalSign이 연결돼
// "vital_signs" 섹션을 추가한다 — 이름을 "vitals"로 짓지 않는 것은 Task
// 14 당시의 거부 이유(구조화 데이터 부재)가 해소된 뒤에도 과거 결정과
// 혼동을 피하기 위함이다.
export type ReportSectionId =
  | "patient_info"
  | "selected_encounter"
  | "vital_signs"
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
