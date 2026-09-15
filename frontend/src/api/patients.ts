import { apiGet } from "./client";

// 백엔드 AssignedPatientOut과 정확히 일치해야 하는 최소 필드만 정의한다 —
// 임상기록 본문이나 다른 의료진 정보는 여기에도, 화면에도 없다.
export type AssignedPatient = {
  id: number;
  mrn: string;
  name: string;
  birth_date: string;
  assignment_role: string;
};

export function getAssignedPatients(): Promise<AssignedPatient[]> {
  return apiGet<AssignedPatient[]>("/patients/assigned");
}
