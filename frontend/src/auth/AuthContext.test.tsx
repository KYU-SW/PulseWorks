import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider, useAuth } from "./AuthContext";
import { getStoredToken, setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";

function Probe() {
  const { isAuthenticated, role, login, logout } = useAuth();
  return (
    <div>
      <p>authenticated: {String(isAuthenticated)}</p>
      <p>role: {String(role)}</p>
      <button onClick={() => login("a@example.test", "pw").catch(() => {})}>do-login</button>
      <button onClick={logout}>do-logout</button>
    </div>
  );
}

function renderProbe() {
  return render(
    <AuthProvider>
      <Probe />
    </AuthProvider>
  );
}

describe("AuthContext", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  it("restores authenticated state from a valid stored token on mount", () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    renderProbe();

    expect(screen.getByText("authenticated: true")).toBeInTheDocument();
    expect(screen.getByText("role: DOCTOR")).toBeInTheDocument();
  });

  it("clears an expired stored token on mount instead of trusting it", () => {
    setStoredToken(makeFakeJwt("DOCTOR", -60));
    renderProbe();

    expect(screen.getByText("authenticated: false")).toBeInTheDocument();
    expect(getStoredToken()).toBeNull();
  });

  it("clears a malformed stored token on mount", () => {
    setStoredToken("garbage");
    renderProbe();

    expect(screen.getByText("authenticated: false")).toBeInTheDocument();
    expect(getStoredToken()).toBeNull();
  });

  it("sets authenticated state and stores the token after a successful login()", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ access_token: makeFakeJwt("PATIENT"), token_type: "bearer" }),
      })
    );
    renderProbe();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "do-login" }));

    await waitFor(() => expect(screen.getByText("authenticated: true")).toBeInTheDocument());
    expect(screen.getByText("role: PATIENT")).toBeInTheDocument();
    expect(getStoredToken()).not.toBeNull();
  });

  it("clears state and the stored token on logout()", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    renderProbe();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "do-logout" }));

    expect(screen.getByText("authenticated: false")).toBeInTheDocument();
    expect(getStoredToken()).toBeNull();
  });

  // 12. API 401 응답 시 로그인 상태 초기화 (client.ts가 쏘는 이벤트를 받는지)
  it("resets to unauthenticated when an auth:unauthorized event fires", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    renderProbe();
    expect(screen.getByText("authenticated: true")).toBeInTheDocument();

    act(() => {
      window.dispatchEvent(new Event("auth:unauthorized"));
    });

    await waitFor(() => expect(screen.getByText("authenticated: false")).toBeInTheDocument());
    expect(getStoredToken()).toBeNull();
  });
});
