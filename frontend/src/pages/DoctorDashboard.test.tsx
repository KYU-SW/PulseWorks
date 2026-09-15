import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { getStoredToken, setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import ProtectedRoute from "../routes/ProtectedRoute";
import DoctorDashboard from "./DoctorDashboard";

const SAMPLE_PATIENTS = [
  { id: 1, mrn: "SYN-0001", name: "합성환자-내분비01", birth_date: "1968-04-12", assignment_role: "ATTENDING_PHYSICIAN" },
  { id: 4, mrn: "SYN-0004", name: "합성환자-일반01", birth_date: "1975-05-01", assignment_role: "ATTENDING_PHYSICIAN" },
];

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

function renderDashboard() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={["/doctor"]}>
        <Routes>
          <Route
            path="/doctor"
            element={
              <ProtectedRoute allowedRoles={["DOCTOR"]}>
                <DoctorDashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/login" element={<div>LOGIN_SCREEN</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("DoctorDashboard", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  it("shows the doctor's role and the required skeleton elements", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, []));
    renderDashboard();

    expect(screen.getByText("의료진 대시보드")).toBeInTheDocument();
    expect(screen.getByText(/DOCTOR/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "로그아웃" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("현재 배정된 환자가 없습니다.")).toBeInTheDocument());
  });

  // 1. DoctorDashboard 로딩 상태
  it("shows a loading state before the patient list resolves", () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_PATIENTS));
    renderDashboard();

    expect(screen.getByText("담당 환자 목록을 불러오는 중...")).toBeInTheDocument();
  });

  // 2. 담당 환자 API 호출 (+ Bearer 토큰 포함)
  it("calls GET /patients/assigned with the Bearer token on mount", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchOnce(200, SAMPLE_PATIENTS);
    vi.stubGlobal("fetch", fetchMock);
    renderDashboard();

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/patients/assigned");
    expect(options.method).toBe("GET");
    expect(options.headers.Authorization).toMatch(/^Bearer /);
  });

  // 3 & 4. 환자 목록 정상 렌더링 + 이름/MRN/생년월일 표시
  it("renders the assigned patients with name, MRN, and birth date", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_PATIENTS));
    renderDashboard();

    expect(await screen.findByText(/합성환자-내분비01/)).toBeInTheDocument();
    expect(screen.getByText(/SYN-0001/)).toBeInTheDocument();
    expect(screen.getByText(/1968-04-12/)).toBeInTheDocument();
    expect(screen.getByText(/합성환자-일반01/)).toBeInTheDocument();
  });

  it("links to the patient's detail timeline page", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_PATIENTS));
    renderDashboard();

    await screen.findByText(/합성환자-내분비01/);
    const detailLinks = screen.getAllByRole("link", { name: "상세보기" });
    expect(detailLinks).toHaveLength(SAMPLE_PATIENTS.length);
    expect(detailLinks[0]).toHaveAttribute("href", "/doctor/patients/1");
  });

  // 5. 합성 데이터 안내 표시
  it("shows the synthetic-data disclaimer", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_PATIENTS));
    renderDashboard();

    expect(await screen.findByText(/합성\(가짜\) 교육용 데이터/)).toBeInTheDocument();
  });

  // 6. 빈 목록 상태 (오류처럼 보이지 않아야 함)
  it("shows a friendly empty state, not an error, when there are no assigned patients", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, []));
    renderDashboard();

    const emptyMessage = await screen.findByText("현재 배정된 환자가 없습니다.");
    expect(emptyMessage).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  // 7. 401 응답 시 로그인 상태 정리 및 /login 이동
  it("clears the session and redirects to /login on a 401", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(401, { detail: "Invalid token" }));
    renderDashboard();

    await waitFor(() => expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument());
    expect(getStoredToken()).toBeNull();
  });

  // 8. 403 응답 시 권한 오류 안내 (임상정보 없음)
  it("shows a permission-denied message on a 403, without any clinical data", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(403, { detail: "Forbidden for this role" }));
    renderDashboard();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("담당 환자 목록을 조회할 권한이 없습니다.");
    expect(screen.queryByText(/SYN-/)).not.toBeInTheDocument();
  });

  // 9. 서버 오류 시 일반 오류 메시지 (내부 오류 내용 노출 안 함)
  it("shows a generic error message on a server error, not the raw server detail", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchOnce(500, { detail: "Traceback: something internal broke at line 42" })
    );
    renderDashboard();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).not.toContain("Traceback");
    expect(alert.textContent).not.toContain("line 42");
  });

  // 10. 다시 시도 기능이 있으면 재호출 동작
  it("retries the request when the retry button is clicked", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ detail: "boom" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => SAMPLE_PATIENTS });
    vi.stubGlobal("fetch", fetchMock);
    renderDashboard();
    const user = userEvent.setup();

    await screen.findByRole("alert");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));

    expect(await screen.findByText(/합성환자-내분비01/)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  // 11. 다른 환자의 임상정보를 불필요하게 표시하지 않음
  it("never renders clinical fields that were not requested", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_PATIENTS));
    renderDashboard();

    await screen.findByText(/합성환자-내분비01/);
    expect(screen.queryByText(/진단|처방|Diagnosis|Prescription/)).not.toBeInTheDocument();
  });

  // 12. JWT와 비밀번호가 화면 또는 로그에 노출되지 않음
  it("never logs the token to the console while loading patients", async () => {
    const token = makeFakeJwt("DOCTOR");
    setStoredToken(token);
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_PATIENTS));
    renderDashboard();

    await screen.findByText(/합성환자-내분비01/);

    for (const call of consoleSpy.mock.calls) {
      expect(call.map(String).join(" ")).not.toContain(token);
    }
    consoleSpy.mockRestore();
  });

  it("clears the stored token and navigates to /login on logout", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, []));
    renderDashboard();
    await screen.findByText("현재 배정된 환자가 없습니다.");
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "로그아웃" }));

    expect(getStoredToken()).toBeNull();
    expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument();
  });
});
