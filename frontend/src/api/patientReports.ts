// backend/app/schemas/patient_report.py의 화이트리스트 스키마와 정확히
// 일치해야 하는 타입. app/api/clinicalReports.ts(의사용)를 재사용하거나
// 상속하지 않는다 — 환자용 응답에는 내부 id, rule_id, source_type,
// handoff_note, source_record_ids, SafetyAlert/ClinicalNote 필드가
// 애초에 존재하지 않는다.

import { apiGet } from "./client";

export type PatientReportListItem = {
  id: number;
  report_type: string;
  department: string;
  encounter_date: string;
  reviewed_at: string;
};

export type PatientDiagnosis = {
  description: string;
  diagnosed_at: string;
};

export type PatientLabResult = {
  test_name: string;
  value: number;
  unit: string;
  reference_low: number;
  reference_high: number;
  measured_at: string;
  status: string;
};

export type PatientLabTrendPoint = {
  value: number;
  unit: string;
  reference_low: number;
  reference_high: number;
  measured_at: string;
  status: string;
};

export type PatientLabTrendGroup = {
  test_name: string;
  unit: string;
  points: PatientLabTrendPoint[];
};

export type PatientPrescription = {
  medication_name: string;
  dosage: string;
  prescribed_at: string;
};

export type PatientAllergy = {
  substance: string;
  reaction: string;
  severity: string;
};

export type PatientClinicalReportDetail = {
  id: number;
  department: string;
  encounter_type: string;
  encounter_date: string;
  reviewed_at: string;
  narrative: string | null;
  patient_guidance: string | null;
  diagnoses: PatientDiagnosis[];
  lab_results: PatientLabResult[];
  lab_trends: PatientLabTrendGroup[];
  prescriptions: PatientPrescription[];
  allergies: PatientAllergy[];
  evidence: string[];
  safety_notice: string;
};

export function getPatientReports(): Promise<PatientReportListItem[]> {
  return apiGet<PatientReportListItem[]>("/patient/reports");
}

export function getPatientReport(reportId: string | number): Promise<PatientClinicalReportDetail> {
  return apiGet<PatientClinicalReportDetail>(`/patient/reports/${reportId}`);
}
