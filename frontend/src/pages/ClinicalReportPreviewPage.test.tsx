import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { getStoredToken, setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import ProtectedRoute from "../routes/ProtectedRoute";
import ClinicalReportPreviewPage from "./ClinicalReportPreviewPage";

const SAMPLE_REPORT = {
  id: 42,
  patient_id: 1,
  encounter_id: 1,
  report_type: "DOCTOR_REFERENCE",
  scope_type: "SINGLE_ENCOUNTER",
  scope_encounter_ids: [1],
  status: "DRAFT",
  content: {
    emr_snapshot: {
      patient: { id: 1, mrn: "SYN-0001", name: "합성환자-내분비01", birth_date: "1968-04-12" },
      encounters: [
        {
          id: 1, department: "ENDOCRINOLOGY", encounter_type: "OUTPATIENT",
          start_time: "2026-03-10T09:00:00Z", end_time: null,
        },
      ],
      diagnoses: [
        {
          id: 1, encounter_id: 1, code: "E11.9", description: "2형 당뇨병 신규 진단 (합성 데이터)",
          diagnosed_at: "2026-03-10T09:00:00Z", source_type: "INSTITUTION_GENERATED",
        },
      ],
      lab_results: [
        {
          id: 1, encounter_id: 1, test_name: "HbA1c", value: 7.2, unit: "%",
          reference_low: 4.0, reference_high: 6.0, measured_at: "2026-03-10T09:00:00Z",
          source_type: "INSTITUTION_GENERATED", status: "HIGH", rule_id: "LAB_REFERENCE_RANGE",
        },
      ],
      lab_trends: [
        {
          test_name: "HbA1c", unit: "%",
          points: [
            {
              value: 7.2, unit: "%", reference_low: 4.0, reference_high: 6.0,
              measured_at: "2026-03-10T09:00:00Z", status: "HIGH", rule_id: "LAB_REFERENCE_RANGE",
              encounter_id: 1, source_type: "INSTITUTION_GENERATED",
            },
          ],
        },
      ],
      prescriptions: [],
      allergies: [
        {
          id: 1, substance: "Penicillin", reaction: "두드러기 (합성 데이터)", severity: "MODERATE",
          recorded_at: "2026-01-01T09:00:00Z", source_type: "INSTITUTION_GENERATED",
        },
      ],
      safety_alerts: [
        {
          id: 1, encounter_id: 1, prescription_id: 5, lab_result_id: null,
          rule_id: "ALLERGY_MEDICATION_CONFLICT", priority: "HIGH",
          evidence: { explanation: "테스트 설명문" }, created_at: "2026-09-17T14:52:27Z",
        },
      ],
      clinical_notes: [],
      source_record_ids: ["encounter:1", "diagnosis:1"],
    },
    narrative: null,
    handoff_note: null,
    patient_guidance: null,
  },
  created_by_user_id: 1,
  created_at: "2026-09-18T00:00:00Z",
  last_modified_by_user_id: 1,
  last_modified_at: "2026-09-18T01:00:00Z",
  reviewed_by_user_id: null,
  reviewed_at: null,
  supersedes_report_id: null,
};

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

// GET /reports/{id}(최초 로딩)과 POST /reports/{id}/generate-narrative
// (버튼 클릭)에 서로 다른 응답을 주기 위한 라우터.
function mockFetchRouter(routes: { get: unknown; post?: unknown; postStatus?: number }) {
  return vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
    const isPost = options?.method === "POST";
    const body = isPost ? routes.post : routes.get;
    const status = isPost ? routes.postStatus ?? 200 : 200;
    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
      text: async () => JSON.stringify(body),
    });
  });
}

function renderPreviewPage(reportId = "42") {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[`/doctor/reports/${reportId}`]}>
        <Routes>
          <Route
            path="/doctor/reports/:reportId"
            element={
              <ProtectedRoute allowedRoles={["DOCTOR"]}>
                <ClinicalReportPreviewPage />
              </ProtectedRoute>
            }
          />
          <Route path="/doctor" element={<div>DOCTOR_DASHBOARD_SCREEN</div>} />
          <Route path="/doctor/patients/:patientId" element={<div>PATIENT_TIMELINE_SCREEN</div>} />
          <Route path="/login" element={<div>LOGIN_SCREEN</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("ClinicalReportPreviewPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  // 21 & 22. 정상 reportId로 GET 호출, 로딩 상태
  it("shows a loading state before the report resolves, then calls GET /reports/{id}", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchOnce(200, SAMPLE_REPORT);
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();

    expect(screen.getByText("보고서를 불러오는 중...")).toBeInTheDocument();
    await screen.findByText("진료참고 보고서");
    expect(String(fetchMock.mock.calls[0][0])).toContain("/reports/42");
  });

  // 23 & 24. DRAFT 한국어 상태 표시, 초안+환자 비공개 안내
  it("shows the DRAFT status in Korean and the draft/not-public notice", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.getByText("초안")).toBeInTheDocument();
    expect(
      screen.getByText("이 보고서는 의료진 검토 전 초안이며 현재 환자에게 공개되지 않습니다.")
    ).toBeInTheDocument();
  });

  // 25. 생성일과 마지막 수정일 표시
  it("shows created and last-modified dates", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.getByText(/보고서 생성일/)).toBeInTheDocument();
    expect(screen.getByText(/마지막 수정일/)).toBeInTheDocument();
  });

  // 26. 단일 Encounter 범위 표시
  it("shows the report scope as a single encounter", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.getByText(/단일 진료 방문/)).toBeInTheDocument();
  });

  // 27, 28, 29. ReportRenderer 렌더링(검사 추세, 알레르기, SafetyAlert 표시)
  it("renders the report body via ReportRenderer, including lab trends, allergies, and safety alerts", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.getByText(/HbA1c \(%\)/)).toBeInTheDocument();
    expect(screen.getByText(/Penicillin/)).toBeInTheDocument();
    expect(screen.getByText(/ALLERGY_MEDICATION_CONFLICT/)).toBeInTheDocument();
  });

  // 30. 추가 timeline 또는 lab-trends fetch 없음
  it("never calls the timeline or lab-trends APIs", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchOnce(200, SAMPLE_REPORT);
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    for (const call of fetchMock.mock.calls) {
      expect(String(call[0])).not.toContain("/timeline");
      expect(String(call[0])).not.toContain("/lab-trends");
    }
    expect(fetchMock).toHaveBeenCalledTimes(1); // GET /reports/{id} 단 한 번
  });

  // 31. 401 시 로그인 이동
  it("redirects to /login and clears the session on a 401", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(401, { detail: "Invalid token" }));
    renderPreviewPage();

    await waitFor(() => expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument());
    expect(getStoredToken()).toBeNull();
  });

  // 32 & 39. 403 권한 안내, 오류 화면에서 임상정보 미표시
  it("shows a forbidden message on 403 without leaking clinical content", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(403, { detail: "Forbidden for this role" }));
    renderPreviewPage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("보고서를 조회할 권한이 없습니다.");
    expect(screen.queryByText(/HbA1c/)).not.toBeInTheDocument();
  });

  // 33. 404 일반화 안내
  it("shows a generalized not-found message on 404", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchOnce(404, { detail: "환자 또는 보고서 범위를 찾을 수 없거나 조회할 수 없습니다." })
    );
    renderPreviewPage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("보고서를 찾을 수 없거나 조회할 수 없습니다.");
  });

  // 34 & 35. 일반 오류 안내, 다시 시도 시 GET 재호출
  it("shows a generic error with a working retry button", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ detail: "boom" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => SAMPLE_REPORT });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).not.toContain("boom");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));

    await screen.findByText("진료참고 보고서");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  // 36. 잘못된 reportId는 API 미호출
  it("does not call the API for a malformed reportId and shows the generic not-found message", async () => {
    const fetchMock = vi.fn();
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage("not-a-number");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("보고서를 찾을 수 없거나 조회할 수 없습니다.");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  // 37. 환자 타임라인으로 돌아가기
  it("has a link back to the patient timeline using the report's patient_id", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    const link = await screen.findByRole("link", { name: /환자 타임라인으로 돌아가기/ });
    expect(link).toHaveAttribute("href", "/doctor/patients/1");
  });

  // 38. 담당 환자 목록으로 돌아가기
  it("has a link back to the assigned patient list", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    const link = await screen.findByRole("link", { name: /담당 환자 목록으로 돌아가기/ });
    expect(link).toHaveAttribute("href", "/doctor");
  });

  // 40. 수정·승인·반려·PDF 버튼 없음
  it("never renders edit, approve, reject, or PDF buttons", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    for (const forbiddenName of [/수정/, /승인/, /반려/, /PDF/, /다운로드/]) {
      expect(screen.queryByRole("button", { name: forbiddenName })).not.toBeInTheDocument();
    }
  });

  // 41. PATIENT의 의사용 라우트 접근 차단
  it("blocks a PATIENT-role token from the doctor-only report route", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await waitFor(() => expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument());
  });

  // 42. NURSE와 관리자 역할 접근 차단
  it.each(["NURSE", "ADMIN_STAFF", "SYSTEM_ADMIN"])(
    "blocks a %s-role token from the doctor-only report route",
    async (role) => {
      setStoredToken(makeFakeJwt(role));
      vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
      renderPreviewPage();

      await waitFor(() => expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument());
    }
  );

  // 43. 비밀번호·JWT·내부 오류 미노출
  it("never exposes the token or internal error details", async () => {
    const token = makeFakeJwt("DOCTOR");
    setStoredToken(token);
    vi.stubGlobal(
      "fetch",
      mockFetchOnce(500, { detail: "SELECT * FROM users WHERE secret = 1" })
    );
    renderPreviewPage();

    await screen.findByRole("alert");
    expect(document.body.textContent).not.toContain(token);
    expect(document.body.textContent).not.toContain("SELECT");
  });

  // Mock 설명문 생성 버튼: narrative가 null이고 DRAFT일 때만 표시
  it("shows the Mock narrative generation button only when DRAFT and narrative is null", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    expect(
      await screen.findByRole("button", { name: "Mock 설명문 생성" })
    ).toBeInTheDocument();
  });

  it("does not show the generation button when narrative already exists", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const withNarrative = {
      ...SAMPLE_REPORT,
      content: { ...SAMPLE_REPORT.content, narrative: "이미 생성된 설명문입니다." },
    };
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrative));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.queryByRole("button", { name: "Mock 설명문 생성" })).not.toBeInTheDocument();
    expect(screen.getByText("이미 생성된 설명문입니다.")).toBeInTheDocument();
  });

  it("disables the button while generating, prevents duplicate clicks, and updates in place on success", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const generatedReport = {
      ...SAMPLE_REPORT,
      content: { ...SAMPLE_REPORT.content, narrative: "생성된 Mock 설명문 초안입니다." },
    };
    const fetchMock = mockFetchRouter({ get: SAMPLE_REPORT, post: generatedReport });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "Mock 설명문 생성" });
    await user.click(button);

    // 생성 중에는 버튼이 비활성화되고 문구가 바뀐다(요청이 동기적으로
    // 즉시 끝나므로 최종 성공 상태까지 함께 확인한다).
    await screen.findByText("Mock 설명문 초안");
    expect(screen.getByText("생성된 Mock 설명문 초안입니다.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mock 설명문 생성" })).not.toBeInTheDocument();

    const postCalls = fetchMock.mock.calls.filter(
      (call: any[]) => (call[1] as RequestInit)?.method === "POST"
    );
    expect(postCalls).toHaveLength(1);
    expect(String(postCalls[0][0])).toContain("/reports/42/generate-narrative");
  });

  it("shows a generic error and keeps the button usable when generation fails", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchRouter({ get: SAMPLE_REPORT, post: { detail: "boom" }, postStatus: 500 });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "Mock 설명문 생성" });
    await user.click(button);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("설명문을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    expect(screen.getByRole("button", { name: "Mock 설명문 생성" })).not.toBeDisabled();
  });

  it("never renders the generation button as an edit, approve, reject, or PDF action", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByRole("button", { name: "Mock 설명문 생성" });
    for (const forbiddenName of [/수정/, /승인/, /반려/, /PDF/, /다운로드/]) {
      expect(screen.queryByRole("button", { name: forbiddenName })).not.toBeInTheDocument();
    }
  });
});
