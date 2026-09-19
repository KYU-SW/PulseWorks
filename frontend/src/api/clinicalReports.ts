// backend/app/schemas/clinical_report.py의 Pydantic 스키마와 정확히
// 일치해야 하는 타입.

import { apiGet, apiPatch, apiPost } from "./client";

export type SnapshotPatient = {
  id: number;
  mrn: string;
  name: string;
  birth_date: string;
};

export type SnapshotEncounter = {
  id: number;
  department: string;
  encounter_type: string;
  start_time: string;
  end_time: string | null;
};

export type SnapshotDiagnosis = {
  id: number;
  encounter_id: number;
  code: string;
  description: string;
  diagnosed_at: string;
  source_type: string;
};

export type SnapshotLabResult = {
  id: number;
  encounter_id: number;
  test_name: string;
  value: number;
  unit: string;
  reference_low: number;
  reference_high: number;
  measured_at: string;
  source_type: string;
  status: string;
  rule_id: string;
};

export type SnapshotLabTrendPoint = {
  value: number;
  unit: string;
  reference_low: number;
  reference_high: number;
  measured_at: string;
  status: string;
  rule_id: string;
  encounter_id: number;
  source_type: string;
};

export type SnapshotLabTrendGroup = {
  test_name: string;
  unit: string;
  points: SnapshotLabTrendPoint[];
};

export type SnapshotPrescription = {
  id: number;
  encounter_id: number;
  medication_name: string;
  dosage: string;
  prescribed_by_user_id: number;
  prescribed_at: string;
  source_type: string;
};

export type SnapshotAllergy = {
  id: number;
  substance: string;
  reaction: string;
  severity: string;
  recorded_at: string;
  source_type: string;
};

export type SnapshotSafetyAlert = {
  id: number;
  encounter_id: number;
  prescription_id: number | null;
  lab_result_id: number | null;
  rule_id: string;
  priority: string;
  evidence: Record<string, unknown>;
  created_at: string;
};

export type SnapshotClinicalNote = {
  id: number;
  encounter_id: number;
  author_user_id: number;
  preview_text: string;
  created_at: string;
  source_type: string;
};

export type EmrSnapshot = {
  patient: SnapshotPatient;
  encounters: SnapshotEncounter[];
  diagnoses: SnapshotDiagnosis[];
  lab_results: SnapshotLabResult[];
  lab_trends: SnapshotLabTrendGroup[];
  prescriptions: SnapshotPrescription[];
  allergies: SnapshotAllergy[];
  safety_alerts: SnapshotSafetyAlert[];
  clinical_notes: SnapshotClinicalNote[];
  source_record_ids: string[];
};

export type ReportContentSnapshot = {
  emr_snapshot: EmrSnapshot;
  narrative: string | null;
  handoff_note: string | null;
  patient_guidance: string | null;
};

export type ClinicalReportOut = {
  id: number;
  patient_id: number;
  encounter_id: number | null;
  report_type: string;
  scope_type: string;
  scope_encounter_ids: number[];
  status: string;
  content: ReportContentSnapshot;
  created_by_user_id: number;
  created_at: string;
  last_modified_by_user_id: number;
  last_modified_at: string;
  reviewed_by_user_id: number | null;
  reviewed_at: string | null;
  supersedes_report_id: number | null;
};

export type ClinicalReportCreateRequest = {
  report_type: "DOCTOR_REFERENCE";
  scope_type: "SINGLE_ENCOUNTER";
  encounter_ids: number[];
};

// 백엔드는 신규 생성 시 201, 기존 DRAFT 재사용 시 200을 반환하지만
// client.ts의 apiPost()는 두 상태 모두 response.ok(2xx)로 성공 처리해
// 파싱된 본문을 그대로 반환한다 — 별도 분기 없이 두 경우 다 성공으로
// 다룰 수 있다.
export function createClinicalReport(
  patientId: string | number,
  request: ClinicalReportCreateRequest
): Promise<ClinicalReportOut> {
  return apiPost<ClinicalReportOut>(`/patients/${patientId}/reports`, request);
}

export function getClinicalReport(reportId: string | number): Promise<ClinicalReportOut> {
  return apiGet<ClinicalReportOut>(`/reports/${reportId}`);
}

// 요청 본문이 필요 없는 액션형 엔드포인트 — 빈 객체를 보낸다(백엔드는
// 이 엔드포인트에 요청 본문 파라미터를 두지 않으므로 무시된다).
// narrative가 이미 있으면 백엔드가 그대로 기존 보고서를 200으로
// 반환한다(멱등) — 강제 재생성 API는 없다.
export function generateReportNarrative(reportId: string | number): Promise<ClinicalReportOut> {
  return apiPost<ClinicalReportOut>(`/reports/${reportId}/generate-narrative`, {});
}

// 세 서술형 필드 중 실제로 넘긴 것만 백엔드가 반영한다(model_fields_set
// 기준) — 이 타입에서 세 필드를 전부 선택적(optional)으로 둔 것도 그
// 구분을 그대로 표현하기 위해서다. 프론트는 항상 세 필드를 함께
// 보내도록 설계하지만(저장 버튼 하나로 통합 제출), 타입 자체는 부분
// 업데이트도 표현할 수 있어야 한다.
export type ClinicalReportPatchRequest = {
  narrative?: string | null;
  handoff_note?: string | null;
  patient_guidance?: string | null;
};

export function patchClinicalReport(
  reportId: string | number,
  request: ClinicalReportPatchRequest
): Promise<ClinicalReportOut> {
  return apiPatch<ClinicalReportOut>(`/reports/${reportId}`, request);
}

export function approveClinicalReport(reportId: string | number): Promise<ClinicalReportOut> {
  return apiPost<ClinicalReportOut>(`/reports/${reportId}/approve`, {});
}

export function rejectClinicalReport(reportId: string | number): Promise<ClinicalReportOut> {
  return apiPost<ClinicalReportOut>(`/reports/${reportId}/reject`, {});
}
