import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { getStoredToken, setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import ProtectedRoute from "../routes/ProtectedRoute";
import PatientTimelinePage from "./PatientTimelinePage";

const SAMPLE_TIMELINE = {
  patient: { id: 1, mrn: "SYN-0001", name: "합성환자-내분비01", birth_date: "1968-04-12" },
  timeline: [
    {
      id: 3,
      encounter_id: 3,
      event_type: "LAB_RESULT",
      event_time: "2026-09-05T09:00:00+00:00",
      title: "HbA1c",
      // 실제 백엔드는 값/단위/참고범위만 표시하고 이상 여부는 판정하지
      // 않는다(Task 9 전담) — 목 데이터도 그 계약과 일치시킨다.
      summary: "8.1% (참고범위 4.0-6.0%)",
      source_type: "INSTITUTION_GENERATED",
      department: "내분비내과",
    },
    {
      id: 1,
      encounter_id: 1,
      event_type: "ENCOUNTER",
      event_time: "2026-03-10T09:00:00+00:00",
      title: "내분비내과 외래 방문",
      summary: "내분비내과 외래 방문 (합성 데이터)",
      source_type: null,
      department: "내분비내과",
    },
  ],
};

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

function renderTimelinePage(patientId = "1") {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[`/doctor/patients/${patientId}`]}>
        <Routes>
          <Route
            path="/doctor/patients/:patientId"
            element={
              <ProtectedRoute allowedRoles={["DOCTOR"]}>
                <PatientTimelinePage />
              </ProtectedRoute>
            }
          />
          <Route path="/doctor" element={<div>DOCTOR_DASHBOARD_SCREEN</div>} />
          <Route path="/login" element={<div>LOGIN_SCREEN</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("PatientTimelinePage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  it("shows a loading state before the timeline resolves", () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_TIMELINE));
    renderTimelinePage();

    expect(screen.getByText("환자 타임라인을 불러오는 중...")).toBeInTheDocument();
  });

  it("renders the patient header and the synthetic-data disclaimer on success", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_TIMELINE));
    renderTimelinePage();

    expect(await screen.findByText("합성환자-내분비01")).toBeInTheDocument();
    expect(screen.getByText(/SYN-0001/)).toBeInTheDocument();
    expect(screen.getByText(/1968-04-12/)).toBeInTheDocument();
    expect(screen.getByText(/합성\(가짜\) 교육용 데이터/)).toBeInTheDocument();
  });

  it("shows Korean labels for each event type and the lab value in the summary", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_TIMELINE));
    renderTimelinePage();

    await screen.findByText("합성환자-내분비01");
    expect(screen.getByText("검사결과")).toBeInTheDocument(); // LAB_RESULT
    expect(screen.getByText("방문")).toBeInTheDocument(); // ENCOUNTER
    expect(screen.getByText(/8\.1%/)).toBeInTheDocument();
  });

  it("shows a friendly empty state when the timeline has no items", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchOnce(200, { patient: SAMPLE_TIMELINE.patient, timeline: [] })
    );
    renderTimelinePage();

    expect(await screen.findByText("표시할 타임라인 항목이 없습니다.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("redirects to /login and clears the session on a 401", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(401, { detail: "Invalid token" }));
    renderTimelinePage();

    await waitFor(() => expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument());
    expect(getStoredToken()).toBeNull();
  });

  it("shows a permission-denied message on a 403, without clinical data", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(403, { detail: "Not authorized for this patient" }));
    renderTimelinePage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("이 환자의 타임라인을 조회할 권한이 없습니다.");
    expect(screen.queryByText(/HbA1c/)).not.toBeInTheDocument();
  });

  it("shows a not-found message on a 404", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(404, { detail: "Patient not found" }));
    renderTimelinePage("999999");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("환자를 찾을 수 없습니다.");
  });

  it("shows a generic error message with a working retry button on a server error", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ detail: "boom" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => SAMPLE_TIMELINE });
    vi.stubGlobal("fetch", fetchMock);
    renderTimelinePage();
    const user = userEvent.setup();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).not.toContain("boom");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));

    expect(await screen.findByText("합성환자-내분비01")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("has a link back to the assigned patient list", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_TIMELINE));
    renderTimelinePage();

    const backLink = await screen.findByRole("link", { name: /담당 환자 목록으로 돌아가기/ });
    expect(backLink).toHaveAttribute("href", "/doctor");
  });

  it("never logs the token to the console while loading the timeline", async () => {
    const token = makeFakeJwt("DOCTOR");
    setStoredToken(token);
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_TIMELINE));
    renderTimelinePage();

    await screen.findByText("합성환자-내분비01");

    for (const call of consoleSpy.mock.calls) {
      expect(call.map(String).join(" ")).not.toContain(token);
    }
    consoleSpy.mockRestore();
  });
});
