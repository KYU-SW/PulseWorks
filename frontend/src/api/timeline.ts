import { apiGet } from "./client";

export type TimelineEventType =
  | "ENCOUNTER"
  | "DIAGNOSIS"
  | "LAB_RESULT"
  | "PRESCRIPTION"
  | "CLINICAL_NOTE";

export type TimelinePatient = {
  id: number;
  mrn: string;
  name: string;
  birth_date: string;
};

// 백엔드 TimelineItemOut과 정확히 일치해야 하는 필드만 정의한다.
export type TimelineItem = {
  id: number;
  encounter_id: number;
  event_type: TimelineEventType;
  event_time: string;
  title: string;
  summary: string;
  source_type: string | null;
  department: string;
};

export type PatientTimeline = {
  patient: TimelinePatient;
  timeline: TimelineItem[];
};

export function getPatientTimeline(patientId: string | number): Promise<PatientTimeline> {
  return apiGet<PatientTimeline>(`/patients/${patientId}/timeline`);
}
