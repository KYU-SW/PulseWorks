import { describe, expect, it } from "vitest";
import { findMedication } from "./findMedication";

describe("findMedication", () => {
  it("matches Metformin exactly", () => {
    expect(findMedication("Metformin")?.id).toBe("metformin");
  });

  it("is case-insensitive", () => {
    expect(findMedication("metformin")?.id).toBe("metformin");
    expect(findMedication("METFORMIN")?.id).toBe("metformin");
  });

  it("matches Penicillin V exactly", () => {
    expect(findMedication("Penicillin V")?.id).toBe("penicillin_v");
  });

  it("trims surrounding whitespace before matching", () => {
    expect(findMedication("  Metformin  ")?.id).toBe("metformin");
  });

  it("never matches a name that is only a substring or a variant without an explicit alias", () => {
    expect(findMedication("Metformin XR")).toBeNull();
    expect(findMedication("Penicillin")).toBeNull();
  });

  it("returns null for the development-only test medication string", () => {
    expect(findMedication("Task10VerifyNonConflictMedX")).toBeNull();
  });

  it("returns null for an unregistered medication", () => {
    expect(findMedication("Ibuprofen")).toBeNull();
  });

  it("returns null for an empty or whitespace-only string", () => {
    expect(findMedication("")).toBeNull();
    expect(findMedication("   ")).toBeNull();
  });
});
