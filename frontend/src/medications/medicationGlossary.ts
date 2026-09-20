import { MedicationDefinition } from "./types";

// 모든 약물 설명 다이얼로그에 공통으로 표시하는 안전 안내 — 사용자가
// 승인한 정확한 문구를 그대로 사용한다.
export const MEDICATION_SAFETY_NOTICE =
  "이 설명은 약물의 일반적인 이해를 돕기 위한 정보입니다.\n" +
  "실제 처방 목적과 복용 방법은 담당 의료진 또는 약사에게 확인하세요.";

// 검증되지 않은 기관 검토·의료진 검수·공식 인증 표현을 만들지 않는다 —
// 모든 항목이 같은 일반 라벨을 공유한다(Task 18 glossary.ts와 동일한
// 정책).
const SOURCE_LABEL = "교육용 환자 이해 지원 설명";

// 이 사전의 어떤 설명도 개인별 처방 목적, 복용 횟수, 효능, 안전성,
// 중단 여부를 포함하지 않는다 — 검토 가능한 공공 환자교육 자료를
// 참고한 짧은 일반 설명일 뿐이다(medicationGlossary.test.ts가 이를
// 검증한다).
export const MEDICATIONS: MedicationDefinition[] = [
  {
    id: "metformin",
    genericName: "Metformin",
    displayName: "메트포르민(Metformin)",
    aliases: [],
    plainDefinition: "혈당 조절을 위해 사용될 수 있는 약물입니다.",
    caution: null,
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "penicillin_v",
    genericName: "Penicillin V",
    displayName: "페니실린 V(Penicillin V)",
    aliases: [],
    plainDefinition: "특정 세균 감염 치료에 사용되는 페니실린 계열 항생제입니다.",
    caution: null,
    sourceLabel: SOURCE_LABEL,
  },
];
