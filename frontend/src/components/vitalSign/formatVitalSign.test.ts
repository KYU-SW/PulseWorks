import { describe, expect, it } from "vitest";
import { formatVitalSignDisplayUnit, formatVitalSignValue } from "./formatVitalSign";

describe("formatVitalSignDisplayUnit", () => {
  it("shows Cel as the Korean-friendly ℃ symbol", () => {
    expect(formatVitalSignDisplayUnit("Cel")).toBe("℃");
  });

  it("leaves other canonical units unchanged", () => {
    expect(formatVitalSignDisplayUnit("mmHg")).toBe("mmHg");
    expect(formatVitalSignDisplayUnit("cm")).toBe("cm");
    expect(formatVitalSignDisplayUnit("kg")).toBe("kg");
    expect(formatVitalSignDisplayUnit("/min")).toBe("/min");
    expect(formatVitalSignDisplayUnit("%")).toBe("%");
  });
});

describe("formatVitalSignValue", () => {
  // Backend가 보내는 정밀도 보존 문자열("72.000" 등)을 받아서, 화면에는
  // 원본 문자열을 덮어쓰지 않고 새 표시용 문자열만 만든다.
  it("rounds blood pressure components to whole numbers", () => {
    expect(formatVitalSignValue("BLOOD_PRESSURE", "120.000", "80.000", "mmHg")).toBe(
      "120/80 mmHg"
    );
  });

  it("rounds heart rate, respiratory rate, and pulse oximetry to whole numbers", () => {
    expect(formatVitalSignValue("HEART_RATE", "72.000", null, "/min")).toBe("72 /min");
    expect(formatVitalSignValue("RESPIRATORY_RATE", "16.000", null, "/min")).toBe("16 /min");
    expect(formatVitalSignValue("PULSE_OXIMETRY", "98.000", null, "%")).toBe("98%");
  });

  it("rounds height, weight, and temperature to at most one decimal place", () => {
    expect(formatVitalSignValue("BODY_HEIGHT", "170.000", null, "cm")).toBe("170.0 cm");
    expect(formatVitalSignValue("BODY_WEIGHT", "65.000", null, "kg")).toBe("65.0 kg");
    expect(formatVitalSignValue("BODY_TEMPERATURE", "36.500", null, "Cel")).toBe("36.5℃");
  });

  it("never mutates or loses the original precision-preserving string it was given", () => {
    const original = "36.500";
    formatVitalSignValue("BODY_TEMPERATURE", original, null, "Cel");
    expect(original).toBe("36.500"); // 입력 문자열 자체는 그대로다.
  });
});
