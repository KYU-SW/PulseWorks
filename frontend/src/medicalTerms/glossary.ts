import { MedicalTerm } from "./types";

// 모든 용어 설명 다이얼로그에 공통으로 표시하는 안전 안내 — 사용자가
// 승인한 정확한 문구를 그대로 사용한다.
export const MEDICAL_TERM_SAFETY_NOTICE =
  "이 설명은 의학용어의 일반적인 이해를 돕기 위한 정보입니다.\n" +
  "본인의 검사결과와 건강상태에 대한 해석은 담당 의료진에게 확인하세요.";

// 검증되지 않은 기관명·문헌명을 만들지 않는다 — 모든 항목이 같은
// 일반 라벨을 공유한다.
const SOURCE_LABEL = "교육용 환자 이해 지원 설명";

// 이 사전의 어떤 설명도 개인별 진단, 상태 악화·호전 판단, 검사결과의
// 개인별 해석, 치료 권고, 처방 변경·중단 지시, 예후 판단을 포함하지
// 않는다 — glossary.test.ts가 금지 문구로 이를 검증한다.
export const MEDICAL_TERMS: MedicalTerm[] = [
  {
    id: "hba1c",
    term: "HbA1c",
    aliases: [],
    plainDefinition: "지난 2~3개월 동안의 평균 혈당 수준을 보여주는 검사입니다.",
    caution: null,
    relatedTestNames: ["HbA1c"],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "fasting_glucose",
    term: "Fasting Glucose",
    aliases: [],
    plainDefinition: "음식을 먹지 않은 상태에서 측정한 혈당 수치입니다.",
    caution: null,
    relatedTestNames: ["Fasting Glucose"],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "troponin",
    term: "Troponin",
    aliases: [],
    plainDefinition: "심장 근육 손상 여부를 확인할 때 참고하는 혈액 검사 항목입니다.",
    caution: null,
    relatedTestNames: ["Troponin"],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "heart_rate",
    term: "Heart Rate",
    aliases: [],
    plainDefinition: "1분 동안 심장이 뛰는 횟수입니다.",
    caution: null,
    relatedTestNames: ["Heart Rate"],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "reference_range",
    term: "참고범위",
    aliases: [],
    plainDefinition: "건강한 사람들에게서 일반적으로 관찰되는 검사값의 범위입니다.",
    caution: "이 범위를 벗어난다고 해서 반드시 특정 질병을 의미하지는 않습니다.",
    relatedTestNames: [],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "diagnosis",
    term: "진단",
    aliases: [],
    plainDefinition: "의료진이 환자의 상태를 확인하기 위해 기록한 의학적 판단입니다.",
    caution: "이 기록은 담당 의료진의 판단 결과이며, 본인이 임의로 해석하지 마세요.",
    relatedTestNames: [],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "prescription",
    term: "처방",
    aliases: [],
    plainDefinition: "의료진이 환자에게 필요한 약물과 용법을 정해 기록한 내용입니다.",
    caution: "처방 변경이나 중단은 반드시 담당 의료진과 상의하세요.",
    relatedTestNames: [],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "allergy",
    term: "알레르기",
    aliases: [],
    plainDefinition: "특정 물질에 대해 몸이 민감하게 반응할 수 있음을 기록한 정보입니다.",
    caution: "새로운 증상이 나타나면 담당 의료진에게 알리세요.",
    relatedTestNames: [],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "outpatient",
    term: "외래",
    aliases: [],
    plainDefinition: "입원하지 않고 병원을 방문해 진료를 받는 형태입니다.",
    caution: null,
    relatedTestNames: [],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "emergency_care",
    term: "응급 진료",
    // "응급실"은 별개의 표기로 취급한다 — 별칭에 포함하지 않는다.
    aliases: ["응급"],
    plainDefinition: "긴급하게 진료가 필요한 상황에서 받는 진료를 말합니다.",
    caution: null,
    relatedTestNames: [],
    sourceLabel: SOURCE_LABEL,
  },
  {
    id: "follow_up",
    term: "추적관찰",
    aliases: [],
    plainDefinition: "시간에 따른 상태 변화를 확인하기 위해 정기적으로 검사·진료하는 것을 말합니다.",
    caution: null,
    relatedTestNames: [],
    sourceLabel: SOURCE_LABEL,
  },
];
