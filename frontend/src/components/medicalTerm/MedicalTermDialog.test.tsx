import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import MedicalTermButton from "./MedicalTermButton";
import { MEDICAL_TERM_SAFETY_NOTICE, MEDICAL_TERMS } from "../../medicalTerms/glossary";
import { MedicalTerm } from "../../medicalTerms/types";

const REFERENCE_RANGE_TERM = MEDICAL_TERMS.find((t) => t.id === "reference_range")!; // has a caution
const HEART_RATE_TERM = MEDICAL_TERMS.find((t) => t.id === "heart_rate")!; // caution === null

async function openDialog(term: MedicalTerm, label = term.term) {
  const user = userEvent.setup();
  render(<MedicalTermButton term={term}>{label}</MedicalTermButton>);
  await user.click(screen.getByRole("button", { name: new RegExp(label) }));
  return { user };
}

describe("MedicalTermDialog", () => {
  it("uses a native <dialog> opened via showModal, with aria-labelledby pointing at a real title", async () => {
    await openDialog(REFERENCE_RANGE_TERM);

    const dialog = screen.getByRole("dialog", { hidden: true });
    expect(dialog.tagName.toLowerCase()).toBe("dialog");
    expect(dialog).toHaveAttribute("open");

    const labelledBy = dialog.getAttribute("aria-labelledby");
    expect(labelledBy).toBeTruthy();
    const title = document.getElementById(labelledBy!);
    expect(title).not.toBeNull();
    expect(title?.textContent).toBe("참고범위");
  });

  it("shows the plain-language definition and the common safety notice", async () => {
    await openDialog(REFERENCE_RANGE_TERM);

    expect(screen.getByText(REFERENCE_RANGE_TERM.plainDefinition)).toBeInTheDocument();
    expect(
      screen.getByText((_, element) => element?.textContent === MEDICAL_TERM_SAFETY_NOTICE)
    ).toBeInTheDocument();
    expect(screen.getByText(REFERENCE_RANGE_TERM.sourceLabel)).toBeInTheDocument();
  });

  it("shows the caution text when present", async () => {
    await openDialog(REFERENCE_RANGE_TERM);

    expect(screen.getByText(REFERENCE_RANGE_TERM.caution!)).toBeInTheDocument();
  });

  it("shows no caution paragraph when caution is null", async () => {
    expect(HEART_RATE_TERM.caution).toBeNull();
    await openDialog(HEART_RATE_TERM);

    expect(screen.getByText(HEART_RATE_TERM.plainDefinition)).toBeInTheDocument();
  });

  it("renders an HTML-looking string as literal text, never as executed markup", async () => {
    const hostileTerm: MedicalTerm = {
      ...HEART_RATE_TERM,
      plainDefinition: "<script>window.__xss = true;</script>안전한 설명",
    };
    await openDialog(hostileTerm, "심박수-테스트");

    expect((window as unknown as { __xss?: boolean }).__xss).toBeUndefined();
    expect(
      screen.getByText("<script>window.__xss = true;</script>안전한 설명")
    ).toBeInTheDocument();
    expect(document.querySelector("dialog script")).toBeNull();
  });

  it("has an explicit close button that closes the dialog and returns focus to the term button", async () => {
    const { user } = await openDialog(REFERENCE_RANGE_TERM);
    const triggerButton = screen.getByRole("button", { name: /참고범위/ });

    await user.click(screen.getByRole("button", { name: "닫기" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(triggerButton).toHaveFocus();
  });

  it("closes on Escape and returns focus to the term button", async () => {
    const { user } = await openDialog(REFERENCE_RANGE_TERM);
    const triggerButton = screen.getByRole("button", { name: /참고범위/ });

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(triggerButton).toHaveFocus();
  });
});
