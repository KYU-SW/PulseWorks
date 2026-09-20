import { describe, expect, it } from "vitest";
import { MEDICATION_SAFETY_NOTICE, MEDICATIONS } from "./medicationGlossary";

// 개인별 처방 목적·복용 지시·효능·안전성·중단 판단을 암시하는 표현 —
// Task 18 glossary.test.ts의 금지 문구 검증 패턴을 그대로 적용한다.
const BANNED_PHRASES = [
  "복용하세요",
  "복용하십시오",
  "중단하세요",
  "중단하십시오",
  "매일",
  "하루",
  "회 복용",
  "위험합니다",
  "효과가 있습니다",
  "안전합니다",
];

describe("MEDICATIONS glossary", () => {
  it("has a definition for Metformin", () => {
    const metformin = MEDICATIONS.find((m) => m.genericName === "Metformin");
    expect(metformin).toBeDefined();
    expect(metformin?.displayName).toBe("메트포르민(Metformin)");
    expect(metformin?.plainDefinition).toBe("혈당 조절을 위해 사용될 수 있는 약물입니다.");
  });

  it("has a definition for Penicillin V", () => {
    const penicillinV = MEDICATIONS.find((m) => m.genericName === "Penicillin V");
    expect(penicillinV).toBeDefined();
    expect(penicillinV?.displayName).toBe("페니실린 V(Penicillin V)");
    expect(penicillinV?.plainDefinition).toBe(
      "특정 세균 감염 치료에 사용되는 페니실린 계열 항생제입니다."
    );
  });

  it("has a unique id for every medication", () => {
    const ids = MEDICATIONS.map((m) => m.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("has no overlap between genericName/alias strings across different entries", () => {
    const seen = new Map<string, string>();
    for (const entry of MEDICATIONS) {
      for (const label of [entry.genericName, ...entry.aliases]) {
        const key = label.toLowerCase();
        expect(seen.has(key)).toBe(false);
        seen.set(key, entry.id);
      }
    }
  });

  it("has no missing required fields on any medication", () => {
    for (const entry of MEDICATIONS) {
      expect(entry.id.length).toBeGreaterThan(0);
      expect(entry.genericName.trim().length).toBeGreaterThan(0);
      expect(entry.displayName.trim().length).toBeGreaterThan(0);
      expect(Array.isArray(entry.aliases)).toBe(true);
      expect(entry.plainDefinition.trim().length).toBeGreaterThan(0);
      expect(entry.caution === null || entry.caution.trim().length > 0).toBe(true);
      expect(entry.sourceLabel.trim().length).toBeGreaterThan(0);
    }
  });

  it("never fabricates an institution review or clinician-verified claim in sourceLabel", () => {
    for (const entry of MEDICATIONS) {
      expect(entry.sourceLabel).toBe("교육용 환자 이해 지원 설명");
    }
  });

  it("contains no personal dosing/frequency/efficacy/safety/discontinuation phrases", () => {
    for (const entry of MEDICATIONS) {
      const text = `${entry.plainDefinition} ${entry.caution ?? ""}`;
      for (const phrase of BANNED_PHRASES) {
        expect(text).not.toContain(phrase);
      }
    }
  });

  it("contains no HTML-like tags in any displayed text field", () => {
    for (const entry of MEDICATIONS) {
      for (const text of [entry.plainDefinition, entry.caution ?? "", entry.sourceLabel, entry.displayName]) {
        expect(text).not.toMatch(/[<>]/);
      }
    }
  });

  it("exposes the exact required medication safety notice text", () => {
    expect(MEDICATION_SAFETY_NOTICE).toBe(
      "이 설명은 약물의 일반적인 이해를 돕기 위한 정보입니다.\n" +
        "실제 처방 목적과 복용 방법은 담당 의료진 또는 약사에게 확인하세요."
    );
  });
});
