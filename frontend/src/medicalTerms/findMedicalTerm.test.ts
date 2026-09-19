import { describe, expect, it } from "vitest";
import { findMedicalTerm } from "./findMedicalTerm";

describe("findMedicalTerm", () => {
  it("matches an exact registered term", () => {
    expect(findMedicalTerm("HbA1c")?.id).toBe("hba1c");
    expect(findMedicalTerm("참고범위")?.id).toBe("reference_range");
  });

  it("matches an exact registered alias", () => {
    expect(findMedicalTerm("응급")?.id).toBe("emergency_care");
  });

  it("is case-insensitive for English terms", () => {
    expect(findMedicalTerm("hba1c")?.id).toBe("hba1c");
    expect(findMedicalTerm("HBA1C")?.id).toBe("hba1c");
    expect(findMedicalTerm("fasting glucose")?.id).toBe("fasting_glucose");
  });

  it("trims surrounding whitespace before matching", () => {
    expect(findMedicalTerm("  HbA1c  ")?.id).toBe("hba1c");
  });

  it.each([
    ["HbA1c는", "hba1c"],
    ["HbA1c가", "hba1c"],
    ["HbA1c의", "hba1c"],
    ["HbA1c를", "hba1c"],
    ["HbA1c와", "hba1c"],
    ["진단은", "diagnosis"],
    ["진단이", "diagnosis"],
    ["처방을", "prescription"],
    ["외래와", "outpatient"],
    ["알레르기가", "allergy"],
  ])("strips a limited trailing Korean particle: %s -> %s", (input, expectedId) => {
    expect(findMedicalTerm(input)?.id).toBe(expectedId);
  });

  it("never matches a term that is only a substring inside a longer, different word", () => {
    expect(findMedicalTerm("진단서")).toBeNull();
    expect(findMedicalTerm("재진단")).toBeNull();
    expect(findMedicalTerm("외래환자")).toBeNull();
  });

  it("never treats 응급실 as the same term as 응급 진료", () => {
    expect(findMedicalTerm("응급실")).toBeNull();
  });

  it("never scans a free sentence for an embedded term", () => {
    expect(findMedicalTerm("오늘 진단을 받았습니다")).toBeNull();
    expect(findMedicalTerm("이번 외래 진료 결과는 다음과 같습니다")).toBeNull();
  });

  it("returns null for an unregistered term", () => {
    expect(findMedicalTerm("존재하지않는용어")).toBeNull();
    expect(findMedicalTerm("Cholesterol")).toBeNull();
  });

  it("returns null for an empty or whitespace-only string", () => {
    expect(findMedicalTerm("")).toBeNull();
    expect(findMedicalTerm("   ")).toBeNull();
  });
});
