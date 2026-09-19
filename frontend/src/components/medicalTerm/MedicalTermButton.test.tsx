import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import MedicalTermButton from "./MedicalTermButton";
import { MEDICAL_TERMS } from "../../medicalTerms/glossary";

const HBA1C_TERM = MEDICAL_TERMS.find((t) => t.id === "hba1c")!;

describe("MedicalTermButton", () => {
  it("renders a real <button> element with aria-haspopup=dialog", () => {
    render(<MedicalTermButton term={HBA1C_TERM}>HbA1c</MedicalTermButton>);

    const button = screen.getByRole("button", { name: /HbA1c/ });
    expect(button.tagName.toLowerCase()).toBe("button");
    expect(button).toHaveAttribute("type", "button");
    expect(button).toHaveAttribute("aria-haspopup", "dialog");
  });

  it("shows the term text with an underline and an info icon, not color alone", () => {
    render(<MedicalTermButton term={HBA1C_TERM}>HbA1c</MedicalTermButton>);

    const button = screen.getByRole("button", { name: /HbA1c/ });
    const label = screen.getByText("HbA1c");
    expect(label).toHaveStyle({ textDecoration: "underline" });
    expect(button.textContent).toContain("ⓘ");
  });

  it("does not show the dialog until the button is activated", () => {
    render(<MedicalTermButton term={HBA1C_TERM}>HbA1c</MedicalTermButton>);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the dialog on click", async () => {
    const user = userEvent.setup();
    render(<MedicalTermButton term={HBA1C_TERM}>HbA1c</MedicalTermButton>);

    await user.click(screen.getByRole("button", { name: /HbA1c/ }));

    expect(screen.getByRole("dialog", { hidden: true })).toBeInTheDocument();
  });

  it("opens the dialog on Enter when focused", async () => {
    const user = userEvent.setup();
    render(<MedicalTermButton term={HBA1C_TERM}>HbA1c</MedicalTermButton>);

    await user.tab();
    expect(screen.getByRole("button", { name: /HbA1c/ })).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(screen.getByRole("dialog", { hidden: true })).toBeInTheDocument();
  });

  it("opens the dialog on Space when focused", async () => {
    const user = userEvent.setup();
    render(<MedicalTermButton term={HBA1C_TERM}>HbA1c</MedicalTermButton>);

    await user.tab();
    await user.keyboard(" ");

    expect(screen.getByRole("dialog", { hidden: true })).toBeInTheDocument();
  });

  it("does not open the dialog on hover alone", async () => {
    const user = userEvent.setup();
    render(<MedicalTermButton term={HBA1C_TERM}>HbA1c</MedicalTermButton>);

    await user.hover(screen.getByRole("button", { name: /HbA1c/ }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
