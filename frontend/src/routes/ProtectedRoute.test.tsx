import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import ProtectedRoute from "./ProtectedRoute";

function renderAt(path: string) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/login" element={<div>LOGIN_SCREEN</div>} />
          <Route
            path="/doctor"
            element={
              <ProtectedRoute allowedRoles={["DOCTOR"]}>
                <div>DOCTOR_SCREEN</div>
              </ProtectedRoute>
            }
          />
          <Route
            path="/patient"
            element={
              <ProtectedRoute allowedRoles={["PATIENT"]}>
                <div>PATIENT_SCREEN</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("ProtectedRoute", () => {
  afterEach(() => {
    sessionStorage.clear();
  });

  // 7. 로그인하지 않은 사용자의 보호 라우트 접근 차단
  it("redirects an unauthenticated user away from /doctor to /login", () => {
    renderAt("/doctor");
    expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument();
  });

  it("redirects an unauthenticated user away from /patient to /login", () => {
    renderAt("/patient");
    expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument();
  });

  // 8. PATIENT의 /doctor 접근 차단
  it("blocks a PATIENT from /doctor", () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    renderAt("/doctor");
    expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument();
    expect(screen.queryByText("DOCTOR_SCREEN")).not.toBeInTheDocument();
  });

  // 9. DOCTOR의 /patient 접근 차단
  it("blocks a DOCTOR from /patient", () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    renderAt("/patient");
    expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument();
    expect(screen.queryByText("PATIENT_SCREEN")).not.toBeInTheDocument();
  });

  it("lets a DOCTOR reach /doctor", () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    renderAt("/doctor");
    expect(screen.getByText("DOCTOR_SCREEN")).toBeInTheDocument();
  });

  it("lets a PATIENT reach /patient", () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    renderAt("/patient");
    expect(screen.getByText("PATIENT_SCREEN")).toBeInTheDocument();
  });

  it("treats an expired token as unauthenticated", () => {
    setStoredToken(makeFakeJwt("DOCTOR", -10));
    renderAt("/doctor");
    expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument();
  });

  it("treats a malformed token as unauthenticated", () => {
    setStoredToken("not-a-real-jwt");
    renderAt("/doctor");
    expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument();
  });
});
