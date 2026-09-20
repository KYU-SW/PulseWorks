// Task 19 후속 보완: 환자용 처방 표시에서만 쓰이는 정적 약물 사전의
// 타입. Task 18의 medicalTerms 모듈과 완전히 별개다 — 검사명/개념어와
// 약물명은 서로 다른 매칭 규칙과 안전 안내 문구를 쓴다.
export type MedicationId = "metformin" | "penicillin_v";

export interface MedicationDefinition {
  id: MedicationId;
  // 정확 매칭의 기준이 되는 표준 표기 (처방 기록의 medication_name과
  // 동일한 표기, 예: "Metformin", "Penicillin V").
  genericName: string;
  // 화면에 보여줄 한국어 우선 표기 (예: "메트포르민(Metformin)").
  displayName: string;
  // genericName과 별개로 정확히 일치할 수 있는 표기. 부분 문자열이
  // 아니라 전체 문자열이 정확히 같을 때만 매칭된다.
  aliases: string[];
  plainDefinition: string;
  caution: string | null;
  sourceLabel: string;
}
