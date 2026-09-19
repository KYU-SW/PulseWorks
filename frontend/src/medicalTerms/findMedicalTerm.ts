import { MEDICAL_TERMS } from "./glossary";
import { MedicalTerm } from "./types";

// 이 9개만 제한적으로 제거한다 — 모음/자음 받침 이형태 쌍을 모두
// 포함해 "HbA1c는/가/의/를/와"뿐 아니라 "진단은/이/을/과" 같은 순수
// 한국어 용어의 조사 결합도 다룬다. 이 목록에 없는 끝음절은 절대
// 제거하지 않는다 — "진단서"의 "서", "재진단"의 앞쪽 "재" 등은 조사가
// 아니므로 그대로 두면 매칭에 실패하고(부분 문자열 매칭 금지), 이는
// 의도된 동작이다.
const TRAILING_PARTICLES = ["는", "은", "가", "이", "의", "를", "을", "와", "과"];

function buildIndex(): Map<string, MedicalTerm> {
  const index = new Map<string, MedicalTerm>();
  for (const term of MEDICAL_TERMS) {
    index.set(term.term.toLowerCase(), term);
    for (const alias of term.aliases) {
      index.set(alias.toLowerCase(), term);
    }
  }
  return index;
}

const TERM_INDEX = buildIndex();

// 정확 매칭만 수행한다: 자유 문장을 스캔해 그 안에 숨은 용어를 찾지
// 않는다. 입력 문자열 전체가 (다듬고, 영문 대소문자를 무시하고, 필요하면
// 조사 하나를 제거한 뒤) 등록된 term 또는 alias와 완전히 같을 때만
// 매칭한다.
export function findMedicalTerm(rawText: string): MedicalTerm | null {
  const trimmed = rawText.trim();
  if (trimmed === "") return null;

  const normalized = trimmed.toLowerCase();

  const direct = TERM_INDEX.get(normalized);
  if (direct) return direct;

  for (const particle of TRAILING_PARTICLES) {
    if (normalized.endsWith(particle) && normalized.length > particle.length) {
      const stripped = normalized.slice(0, -particle.length);
      const found = TERM_INDEX.get(stripped);
      if (found) return found;
    }
  }

  return null;
}
