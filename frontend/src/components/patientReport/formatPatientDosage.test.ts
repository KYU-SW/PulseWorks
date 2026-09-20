import { describe, expect, it } from "vitest";
import { formatPatientDosage } from "./formatPatientDosage";

describe("formatPatientDosage", () => {
  it("adds a space between the number and mg", () => {
    expect(formatPatientDosage("500mg")).toBe("500 mg");
    expect(formatPatientDosage("1000mg")).toBe("1000 mg");
  });

  it("converts exactly '1 tablet' to '1정'", () => {
    expect(formatPatientDosage("1 tablet")).toBe("1정");
  });

  it("converts a general '{n} tablet(s)' form to '{n}정'", () => {
    expect(formatPatientDosage("2 tablets")).toBe("2정");
  });

  it("never changes the numeric value or unit itself", () => {
    expect(formatPatientDosage("500mg")).toContain("500");
    expect(formatPatientDosage("1 tablet")).toContain("1");
  });

  it("returns an unrecognized dosage string unchanged", () => {
    expect(formatPatientDosage("1 tablet twice daily")).toBe("1 tablet twice daily");
    expect(formatPatientDosage("as needed")).toBe("as needed");
  });
});
