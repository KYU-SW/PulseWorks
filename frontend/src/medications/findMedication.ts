import { MEDICATIONS } from "./medicationGlossary";
import { MedicationDefinition } from "./types";

function buildIndex(): Map<string, MedicationDefinition> {
  const index = new Map<string, MedicationDefinition>();
  for (const medication of MEDICATIONS) {
    index.set(medication.genericName.toLowerCase(), medication);
    for (const alias of medication.aliases) {
      index.set(alias.toLowerCase(), medication);
    }
  }
  return index;
}

const MEDICATION_INDEX = buildIndex();

// 정확 매칭만 수행한다: 부분 문자열 매칭이나 유사도 기반 추측을 하지
// 않는다. 입력 문자열 전체가 (다듬고 영문 대소문자를 무시한 뒤) 등록된
// genericName 또는 alias와 완전히 같을 때만 매칭한다. 예를 들어
// "Metformin XR"은 명시적 alias가 없으므로 null이다.
export function findMedication(rawName: string): MedicationDefinition | null {
  const trimmed = rawName.trim();
  if (trimmed === "") return null;
  return MEDICATION_INDEX.get(trimmed.toLowerCase()) ?? null;
}
