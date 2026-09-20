import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import Navigation from "./Navigation";

function renderNav(role: "DOCTOR" | "PATIENT", onLogout = vi.fn()) {
  return render(
    <MemoryRouter>
      <Navigation role={role} onLogout={onLogout} />
    </MemoryRouter>
  );
}

describe("Navigation", () => {
  it("renders a real nav element with an aria-label", () => {
    renderNav("DOCTOR");
    expect(screen.getByRole("navigation")).toHaveAccessibleName();
  });

  it("shows the DOCTOR link for a DOCTOR", () => {
    renderNav("DOCTOR");
    const link = screen.getByRole("link", { name: "대시보드" });
    expect(link).toHaveAttribute("href", "/doctor");
  });

  it("shows the PATIENT links for a PATIENT", () => {
    renderNav("PATIENT");
    expect(screen.getByRole("link", { name: "포털" })).toHaveAttribute("href", "/patient");
    expect(screen.getByRole("link", { name: "승인된 보고서" })).toHaveAttribute(
      "href",
      "/patient/reports"
    );
  });

  it("does not show PATIENT links for a DOCTOR", () => {
    renderNav("DOCTOR");
    expect(screen.queryByRole("link", { name: "포털" })).not.toBeInTheDocument();
  });

  it("renders logout as a real button, not a link", () => {
    renderNav("DOCTOR");
    const logoutButton = screen.getByRole("button", { name: "로그아웃" });
    expect(logoutButton.tagName.toLowerCase()).toBe("button");
  });

  it("calls onLogout when the logout button is clicked", async () => {
    const onLogout = vi.fn();
    renderNav("DOCTOR", onLogout);
    await userEvent.setup().click(screen.getByRole("button", { name: "로그아웃" }));
    expect(onLogout).toHaveBeenCalledTimes(1);
  });

  it("never renders a navigation link as a button or the logout action as a link", () => {
    renderNav("DOCTOR");
    expect(screen.queryByRole("button", { name: "대시보드" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "로그아웃" })).not.toBeInTheDocument();
  });
});
