import { apiGet } from "./client";

// 백엔드 LabTrendPointOut과 정확히 일치해야 하는 필드만 정의한다.
export type LabTrendStatus = "LOW" | "NORMAL" | "HIGH" | "UNKNOWN";

export type LabTrendPoint = {
  value: number;
  unit: string;
  reference_low: number;
  reference_high: number;
  measured_at: string;
  status: LabTrendStatus;
  rule_id: string;
  encounter_id: number;
  source_type: string;
};

export type LabTrendGroup = {
  test_name: string;
  unit: string;
  points: LabTrendPoint[];
};

export type PatientLabTrends = {
  patient: { id: number; mrn: string; name: string; birth_date: string };
  trends: LabTrendGroup[];
};

export function getPatientLabTrends(patientId: string | number): Promise<PatientLabTrends> {
  return apiGet<PatientLabTrends>(`/patients/${patientId}/lab-trends`);
}
