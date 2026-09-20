import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import MedicationButton from "./MedicationButton";
import { MEDICATIONS, MEDICATION_SAFETY_NOTICE } from "../../medications/medicationGlossary";
import { MedicationDefinition } from "../../medications/types";

const METFORMIN = MEDICATIONS.find((m) => m.id === "metformin")!;
const PENICILLIN_V = MEDICATIONS.find((m) => m.id === "penicillin_v")!;

async function openDialog(medication: MedicationDefinition) {
  const user = userEvent.setup();
  render(<MedicationButton medication={medication}>{medication.displayName}</MedicationButton>);
  await user.click(screen.getByRole("button", { name: new RegExp(medication.displayName.split("(")[0]) }));
  return { user };
}

describe("MedicationDialog", () => {
  it("uses a native <dialog> opened via showModal, with aria-labelledby pointing at a real title", async () => {
    await openDialog(PENICILLIN_V);

    const dialog = screen.getByRole("dialog", { hidden: true });
    expect(dialog.tagName.toLowerCase()).toBe("dialog");
    expect(dialog).toHaveAttribute("open");

    const labelledBy = dialog.getAttribute("aria-labelledby");
    expect(labelledBy).toBeTruthy();
    const title = document.getElementById(labelledBy!);
    expect(title?.textContent).toBe("페니실린 V(Penicillin V)");
  });

  it("shows the plain-language definition and the common medication safety notice", async () => {
    await openDialog(PENICILLIN_V);

    expect(screen.getByText(PENICILLIN_V.plainDefinition)).toBeInTheDocument();
    expect(
      screen.getByText((_, element) => element?.textContent === MEDICATION_SAFETY_NOTICE)
    ).toBeInTheDocument();
    expect(screen.getByText(PENICILLIN_V.sourceLabel)).toBeInTheDocument();
  });

  it("renders an HTML-looking string as literal text, never as executed markup", async () => {
    const hostileMedication: MedicationDefinition = {
      ...METFORMIN,
      plainDefinition: "<script>window.__medXss = true;</script>안전한 설명",
    };
    await openDialog(hostileMedication);

    expect((window as unknown as { __medXss?: boolean }).__medXss).toBeUndefined();
    expect(
      screen.getByText("<script>window.__medXss = true;</script>안전한 설명")
    ).toBeInTheDocument();
    expect(document.querySelector("dialog script")).toBeNull();
  });

  it("has an explicit close button that closes the dialog and returns focus to the medication button", async () => {
    const { user } = await openDialog(METFORMIN);
    const triggerButton = screen.getByRole("button", { name: /메트포르민/ });

    await user.click(screen.getByRole("button", { name: "닫기" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(triggerButton).toHaveFocus();
  });

  it("closes on Escape and returns focus to the medication button", async () => {
    const { user } = await openDialog(METFORMIN);
    const triggerButton = screen.getByRole("button", { name: /메트포르민/ });

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(triggerButton).toHaveFocus();
  });
});
