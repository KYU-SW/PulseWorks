import { apiGet } from "./client";

export type TimelineEventType =
  | "ENCOUNTER"
  | "DIAGNOSIS"
  | "LAB_RESULT"
  | "PRESCRIPTION"
  | "CLINICAL_NOTE"
  | "VITAL_SIGN" // Task F4-A
  // UX-2C: ClinicalReport 공식 상태 전이(승인/반려)만 — narrative/content는
  // 절대 포함하지 않는다. 생성/수정은 임상 타임라인에 오지 않는다.
  | "REPORT_APPROVED"
  | "REPORT_REJECTED";

export type TimelinePatient = {
  id: number;
  mrn: string;
  name: string;
  birth_date: string;
};

// 백엔드 TimelineItemOut과 정확히 일치해야 하는 필드만 정의한다.
//
// Task F4-A: vital_type/value/value_secondary/unit/quality_warnings는
// event_type="VITAL_SIGN"일 때만 값이 있다(그 외 5개 event_type에서는
// null/빈 배열). value/value_secondary는 Decimal을 그대로 직렬화한
// 문자열이다(정밀도 보존 — number가 아니다). bmi는 event_type=
// "ENCOUNTER"일 때만, 계산 가능한 경우에만 값이 있다.
export type TimelineItem = {
  id: number;
  encounter_id: number;
  event_type: TimelineEventType;
  event_time: string;
  title: string;
  summary: string;
  source_type: string | null;
  department: string;
  // 선택적 필드로 둔다 — 백엔드는 항상 null/빈 배열을 포함해 보내지만,
  // 기존(F4-A 이전) 테스트 fixture가 이 필드들을 몰라도 그대로 컴파일
  // 되도록 한다(실제 API 응답과의 차이는 "누락"과 "null"뿐이고, 이
  // 필드들을 읽는 코드는 전부 event_type==="VITAL_SIGN"/"ENCOUNTER"일
  // 때만 접근하므로 안전하다).
  vital_type?: string | null;
  value?: string | null;
  value_secondary?: string | null;
  unit?: string | null;
  quality_warnings?: string[];
  bmi?: string | null;
};

export type PatientTimeline = {
  patient: TimelinePatient;
  timeline: TimelineItem[];
};

export function getPatientTimeline(patientId: string | number): Promise<PatientTimeline> {
  return apiGet<PatientTimeline>(`/patients/${patientId}/timeline`);
}
