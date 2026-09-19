import { describe, expect, it } from "vitest";
import { MEDICAL_TERM_SAFETY_NOTICE, MEDICAL_TERMS } from "./glossary";

// 의료 안전 원칙 위반 소지가 있는 표현 — Task 9/16의 금지 문구 검증
// 패턴을 이 정적 사전에도 그대로 적용한다.
const BANNED_PHRASES = [
  "진단합니다",
  "확진",
  "권장합니다",
  "권고합니다",
  "치료하세요",
  "복용하세요",
  "복용하십시오",
  "중단하십시오",
  "예후는",
  "완치",
  "악화될 것",
  "호전될 것",
];

describe("MEDICAL_TERMS glossary", () => {
  it("has exactly the 11 required initial terms", () => {
    expect(MEDICAL_TERMS).toHaveLength(11);
  });

  it("has a unique id for every term", () => {
    const ids = MEDICAL_TERMS.map((t) => t.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("has no overlap between term/alias strings across different entries", () => {
    const seen = new Map<string, string>();
    for (const entry of MEDICAL_TERMS) {
      for (const label of [entry.term, ...entry.aliases]) {
        const key = label.toLowerCase();
        expect(seen.has(key)).toBe(false);
        seen.set(key, entry.id);
      }
    }
  });

  it("registers 응급 진료 (emergency_care) with alias 응급, and never with 응급실", () => {
    const emergencyCare = MEDICAL_TERMS.find((t) => t.id === "emergency_care");
    expect(emergencyCare).toBeDefined();
    expect(emergencyCare?.term).toBe("응급 진료");
    expect(emergencyCare?.aliases).toContain("응급");
    expect(emergencyCare?.aliases).not.toContain("응급실");
    expect(emergencyCare?.term).not.toBe("응급실");
  });

  it("has no missing required fields on any term", () => {
    for (const entry of MEDICAL_TERMS) {
      expect(entry.id.length).toBeGreaterThan(0);
      expect(entry.term.trim().length).toBeGreaterThan(0);
      expect(Array.isArray(entry.aliases)).toBe(true);
      expect(entry.plainDefinition.trim().length).toBeGreaterThan(0);
      expect(entry.caution === null || entry.caution.trim().length > 0).toBe(true);
      expect(Array.isArray(entry.relatedTestNames)).toBe(true);
      expect(entry.sourceLabel.trim().length).toBeGreaterThan(0);
    }
  });

  it("never fabricates an institution or literature name in sourceLabel", () => {
    for (const entry of MEDICAL_TERMS) {
      expect(entry.sourceLabel).toBe("교육용 환자 이해 지원 설명");
    }
  });

  it("contains no banned diagnostic/treatment-directive phrases in any definition or caution", () => {
    for (const entry of MEDICAL_TERMS) {
      const text = `${entry.plainDefinition} ${entry.caution ?? ""}`;
      for (const phrase of BANNED_PHRASES) {
        expect(text).not.toContain(phrase);
      }
    }
  });

  it("contains no HTML-like tags in any displayed text field", () => {
    for (const entry of MEDICAL_TERMS) {
      for (const text of [entry.plainDefinition, entry.caution ?? "", entry.sourceLabel]) {
        expect(text).not.toMatch(/[<>]/);
      }
    }
  });

  it("connects the four lab terms to their real LabResult.test_name values", () => {
    const byId = Object.fromEntries(MEDICAL_TERMS.map((t) => [t.id, t]));
    expect(byId.hba1c.relatedTestNames).toEqual(["HbA1c"]);
    expect(byId.fasting_glucose.relatedTestNames).toEqual(["Fasting Glucose"]);
    expect(byId.troponin.relatedTestNames).toEqual(["Troponin"]);
    expect(byId.heart_rate.relatedTestNames).toEqual(["Heart Rate"]);
  });

  it("exposes the exact required common safety notice text", () => {
    expect(MEDICAL_TERM_SAFETY_NOTICE).toBe(
      "이 설명은 의학용어의 일반적인 이해를 돕기 위한 정보입니다.\n" +
        "본인의 검사결과와 건강상태에 대한 해석은 담당 의료진에게 확인하세요."
    );
  });
});
