import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import UnsupportedRolePage from "./UnsupportedRolePage";

function renderAt() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={["/unsupported-role"]}>
        <Routes>
          <Route path="/unsupported-role" element={<UnsupportedRolePage />} />
          <Route path="/login" element={<div>LOGIN_SCREEN</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("UnsupportedRolePage", () => {
  afterEach(() => {
    sessionStorage.clear();
  });

  it("shows the title", () => {
    setStoredToken(makeFakeJwt("NURSE"));
    renderAt();
    expect(screen.getByRole("heading", { level: 1, name: "준비 중인 화면입니다" })).toBeInTheDocument();
  });

  it("shows an access-restricted notice naming the role, without leaking token details", () => {
    setStoredToken(makeFakeJwt("NURSE"));
    renderAt();
    expect(screen.getByText(/이 역할\(NURSE\)을 위한 화면은 아직 지원되지 않습니다/)).toBeInTheDocument();
  });

  it("renders the shared Navigation inside a real header", () => {
    setStoredToken(makeFakeJwt("NURSE"));
    renderAt();
    expect(screen.getByRole("banner")).toBeInTheDocument();
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });

  it("renders logout as a real button", () => {
    setStoredToken(makeFakeJwt("NURSE"));
    renderAt();
    const logoutButton = screen.getByRole("button", { name: "로그아웃" });
    expect(logoutButton.tagName.toLowerCase()).toBe("button");
  });

  it("logs out and navigates to /login when the logout button is clicked", async () => {
    setStoredToken(makeFakeJwt("NURSE"));
    renderAt();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "로그아웃" }));

    expect(await screen.findByText("LOGIN_SCREEN")).toBeInTheDocument();
  });
});
