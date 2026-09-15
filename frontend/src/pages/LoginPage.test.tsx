import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import LoginPage from "./LoginPage";
import { makeFakeJwt } from "../test/fakeJwt";

function renderLoginPage() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/doctor" element={<div>DOCTOR_SCREEN</div>} />
          <Route path="/patient" element={<div>PATIENT_SCREEN</div>} />
          <Route path="/unsupported-role" element={<div>UNSUPPORTED_SCREEN</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

function mockLoginFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

describe("LoginPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  // 1. 로그인 페이지 렌더링
  it("renders the required elements", () => {
    renderLoginPage();

    expect(screen.getByText("EMR 프로토타입")).toBeInTheDocument();
    expect(screen.getByText(/교육용 EMR 프로토타입/)).toBeInTheDocument();
    expect(screen.getByText(/합성\(가짜\) 데이터/)).toBeInTheDocument();
    expect(screen.getByText(/실제 의료기관 운영 목적으로 사용되지 않습니다/)).toBeInTheDocument();
    expect(screen.getByLabelText("이메일")).toBeInTheDocument();
    expect(screen.getByLabelText("비밀번호")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "로그인" })).toBeInTheDocument();
  });

  // 2. 이메일과 비밀번호 입력
  it("lets the user type into the email and password fields", async () => {
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("이메일"), "doctor@example.test");
    await user.type(screen.getByLabelText("비밀번호"), "demo1234");

    expect(screen.getByLabelText("이메일")).toHaveValue("doctor@example.test");
    expect(screen.getByLabelText("비밀번호")).toHaveValue("demo1234");
  });

  // 3. 로그인 성공 시 POST /auth/login 호출
  it("calls POST /auth/login with the entered credentials on submit", async () => {
    const fetchMock = mockLoginFetch(200, {
      access_token: makeFakeJwt("DOCTOR"),
      token_type: "bearer",
    });
    vi.stubGlobal("fetch", fetchMock);
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("이메일"), "endocrine.doctor@example.test");
    await user.type(screen.getByLabelText("비밀번호"), "demo1234");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/auth/login");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({
      email: "endocrine.doctor@example.test",
      password: "demo1234",
    });
  });

  // 4. DOCTOR 로그인 성공 시 /doctor 이동
  it("navigates to /doctor when the token's role is DOCTOR", async () => {
    vi.stubGlobal(
      "fetch",
      mockLoginFetch(200, { access_token: makeFakeJwt("DOCTOR"), token_type: "bearer" })
    );
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("이메일"), "endocrine.doctor@example.test");
    await user.type(screen.getByLabelText("비밀번호"), "demo1234");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(await screen.findByText("DOCTOR_SCREEN")).toBeInTheDocument();
  });

  // 5. PATIENT 로그인 성공 시 /patient 이동
  it("navigates to /patient when the token's role is PATIENT", async () => {
    vi.stubGlobal(
      "fetch",
      mockLoginFetch(200, { access_token: makeFakeJwt("PATIENT"), token_type: "bearer" })
    );
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("이메일"), "patient1@example.test");
    await user.type(screen.getByLabelText("비밀번호"), "demo1234");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(await screen.findByText("PATIENT_SCREEN")).toBeInTheDocument();
  });

  it("navigates to /unsupported-role for a role with no dedicated screen yet", async () => {
    vi.stubGlobal(
      "fetch",
      mockLoginFetch(200, { access_token: makeFakeJwt("NURSE"), token_type: "bearer" })
    );
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("이메일"), "nurse1@example.test");
    await user.type(screen.getByLabelText("비밀번호"), "demo1234");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    expect(await screen.findByText("UNSUPPORTED_SCREEN")).toBeInTheDocument();
  });

  // 6. 로그인 실패 메시지 표시 — 이메일 미존재/비밀번호 오류를 구분하지 않는다.
  it("shows a generic failure message on invalid credentials, without echoing the password", async () => {
    vi.stubGlobal("fetch", mockLoginFetch(401, { detail: "Invalid credentials" }));
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("이메일"), "endocrine.doctor@example.test");
    await user.type(screen.getByLabelText("비밀번호"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "로그인" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("이메일 또는 비밀번호가 올바르지 않습니다.");
    expect(alert.textContent).not.toContain("wrong-password");
    expect(screen.queryByText(/Invalid credentials/)).not.toBeInTheDocument();
  });

  // 13. 비밀번호 또는 토큰이 화면과 로그에 노출되지 않음
  it("never logs the password or the issued token to the console", async () => {
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    const token = makeFakeJwt("DOCTOR");
    vi.stubGlobal("fetch", mockLoginFetch(200, { access_token: token, token_type: "bearer" }));
    renderLoginPage();
    const user = userEvent.setup();

    await user.type(screen.getByLabelText("이메일"), "endocrine.doctor@example.test");
    await user.type(screen.getByLabelText("비밀번호"), "super-secret-demo-password");
    await user.click(screen.getByRole("button", { name: "로그인" }));
    await screen.findByText("DOCTOR_SCREEN");

    for (const call of consoleSpy.mock.calls) {
      const joined = call.map(String).join(" ");
      expect(joined).not.toContain("super-secret-demo-password");
      expect(joined).not.toContain(token);
    }
    consoleSpy.mockRestore();
  });
});
