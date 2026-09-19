// Task 18: 환자용 보고서에서 쓰일 정적 의학용어 사전의 타입. 이 파일은
// 어떤 실제 페이지에도 연결되지 않는 독립적인 기반 부품이다 — 실제
// 환자 보고서 연결은 Task 19에서 수행한다.
export type MedicalTermId =
  | "hba1c"
  | "fasting_glucose"
  | "troponin"
  | "heart_rate"
  | "reference_range"
  | "diagnosis"
  | "prescription"
  | "allergy"
  | "outpatient"
  | "emergency_care"
  | "follow_up";

export interface MedicalTerm {
  id: MedicalTermId;
  // 정확 매칭의 기준이 되는 표준 표기 (예: "HbA1c", "응급 진료").
  term: string;
  // term과 별개로 정확히 일치할 수 있는 표기 (예: "응급"). 부분 문자열이
  // 아니라 전체 문자열이 정확히 같을 때만 매칭된다.
  aliases: string[];
  plainDefinition: string;
  // 진단·치료 지시가 아닌, 오해를 줄이기 위한 참고 문구. 없으면 null.
  caution: string | null;
  // 이 용어와 연결되는 실제 LabResult.test_name 값들 (개념어는 빈 배열).
  relatedTestNames: string[];
  sourceLabel: string;
}
