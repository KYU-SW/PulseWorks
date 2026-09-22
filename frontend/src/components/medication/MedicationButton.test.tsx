import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import MedicationButton from "./MedicationButton";
import { MEDICATIONS } from "../../medications/medicationGlossary";

const METFORMIN = MEDICATIONS.find((m) => m.id === "metformin")!;

describe("MedicationButton", () => {
  it("renders a real <button> element with aria-haspopup=dialog", () => {
    render(<MedicationButton medication={METFORMIN}>{METFORMIN.displayName}</MedicationButton>);

    const button = screen.getByRole("button", { name: /메트포르민/ });
    expect(button.tagName.toLowerCase()).toBe("button");
    expect(button).toHaveAttribute("type", "button");
    expect(button).toHaveAttribute("aria-haspopup", "dialog");
  });

  it("shows the display name with an underline and an info icon, not color alone", () => {
    render(<MedicationButton medication={METFORMIN}>{METFORMIN.displayName}</MedicationButton>);

    const button = screen.getByRole("button", { name: /메트포르민/ });
    const label = screen.getByText(METFORMIN.displayName);
    expect(label).toHaveStyle({ textDecoration: "underline" });
    expect(button.textContent).toContain("ⓘ");
  });

  // Task 20C: MedicalTermButton과 동일한 공통 스타일 클래스를 공유한다.
  it("applies the shared ui-term-trigger styling class", () => {
    render(<MedicationButton medication={METFORMIN}>{METFORMIN.displayName}</MedicationButton>);

    const button = screen.getByRole("button", { name: /메트포르민/ });
    expect(button.className).toContain("ui-term-trigger");
  });

  it("does not show the dialog until the button is activated", () => {
    render(<MedicationButton medication={METFORMIN}>{METFORMIN.displayName}</MedicationButton>);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the dialog on click", async () => {
    const user = userEvent.setup();
    render(<MedicationButton medication={METFORMIN}>{METFORMIN.displayName}</MedicationButton>);

    await user.click(screen.getByRole("button", { name: /메트포르민/ }));

    expect(screen.getByRole("dialog", { hidden: true })).toBeInTheDocument();
  });

  it("opens the dialog on Enter when focused", async () => {
    const user = userEvent.setup();
    render(<MedicationButton medication={METFORMIN}>{METFORMIN.displayName}</MedicationButton>);

    await user.tab();
    expect(screen.getByRole("button", { name: /메트포르민/ })).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(screen.getByRole("dialog", { hidden: true })).toBeInTheDocument();
  });

  it("opens the dialog on Space when focused", async () => {
    const user = userEvent.setup();
    render(<MedicationButton medication={METFORMIN}>{METFORMIN.displayName}</MedicationButton>);

    await user.tab();
    await user.keyboard(" ");

    expect(screen.getByRole("dialog", { hidden: true })).toBeInTheDocument();
  });

  it("does not open the dialog on hover alone", async () => {
    const user = userEvent.setup();
    render(<MedicationButton medication={METFORMIN}>{METFORMIN.displayName}</MedicationButton>);

    await user.hover(screen.getByRole("button", { name: /메트포르민/ }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
