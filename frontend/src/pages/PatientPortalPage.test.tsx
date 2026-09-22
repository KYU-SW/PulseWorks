import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import PatientPortalPage from "./PatientPortalPage";

function renderAt() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={["/patient"]}>
        <Routes>
          <Route path="/patient" element={<PatientPortalPage />} />
          <Route path="/login" element={<div>LOGIN_SCREEN</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("PatientPortalPage", () => {
  afterEach(() => {
    sessionStorage.clear();
  });

  it("shows the portal title", () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    renderAt();
    expect(screen.getByRole("heading", { level: 1, name: "환자 포털" })).toBeInTheDocument();
  });

  it("renders the PATIENT Navigation inside a real header", () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    renderAt();
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "승인된 보고서" })).toHaveAttribute(
      "href",
      "/patient/reports"
    );
  });

  it("shows the main call-to-action link to approved reports", () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    renderAt();
    const links = screen.getAllByRole("link", { name: "승인된 보고서 보기" });
    expect(links.length).toBeGreaterThan(0);
    expect(links[0]).toHaveAttribute("href", "/patient/reports");
  });

  it("renders logout as a single real button (no duplicate logout in the body)", () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    renderAt();
    const logoutButtons = screen.getAllByRole("button", { name: "로그아웃" });
    expect(logoutButtons).toHaveLength(1);
    expect(logoutButtons[0].tagName.toLowerCase()).toBe("button");
  });

  it("logs out and navigates to /login when the logout button is clicked", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    renderAt();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "로그아웃" }));

    expect(await screen.findByText("LOGIN_SCREEN")).toBeInTheDocument();
  });
});
