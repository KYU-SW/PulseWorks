import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { getStoredToken, setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import DoctorDashboard from "./DoctorDashboard";

function renderDashboard() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={["/doctor"]}>
        <Routes>
          <Route path="/doctor" element={<DoctorDashboard />} />
          <Route path="/login" element={<div>LOGIN_SCREEN</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("DoctorDashboard", () => {
  afterEach(() => {
    sessionStorage.clear();
  });

  it("shows the doctor's role and the required skeleton elements", () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    renderDashboard();

    expect(screen.getByText("의료진 대시보드")).toBeInTheDocument();
    expect(screen.getByText(/DOCTOR/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "로그아웃" })).toBeInTheDocument();
  });

  // 10. 로그아웃 시 토큰 제거 및 /login 이동
  it("clears the stored token and navigates to /login on logout", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    renderDashboard();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "로그아웃" }));

    expect(getStoredToken()).toBeNull();
    expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument();
  });
});
