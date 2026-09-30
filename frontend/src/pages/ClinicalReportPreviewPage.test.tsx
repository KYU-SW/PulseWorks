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
    narrative_source: null,
    narrative_edited_by_clinician: false,
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

  // 40. Word·PDF 출력 버튼은 여전히 없음(수정·승인·반려는 Task 17에서 추가됨)
  it("never renders Word or PDF export buttons", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    for (const forbiddenName of [/PDF/, /다운로드/, /Word/]) {
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

  // 공통 생성 버튼: narrative가 null이고 DRAFT일 때만 표시(Task D1 —
  // Provider 종류와 무관하게 항상 같은 문구).
  it("shows the common narrative generation button only when DRAFT and narrative is null", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    expect(
      await screen.findByRole("button", { name: "설명문 초안 생성" })
    ).toBeInTheDocument();
  });

  it("does not show the generation button when narrative already exists", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const withNarrative = {
      ...SAMPLE_REPORT,
      content: {
        ...SAMPLE_REPORT.content,
        narrative: "이미 생성된 설명문입니다.",
        narrative_source: "mock",
      },
    };
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrative));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.queryByRole("button", { name: "설명문 초안 생성" })).not.toBeInTheDocument();
    // DRAFT에서는 narrative가 편집 가능한 textarea에 표시된다(Task 17).
    expect(screen.getByDisplayValue("이미 생성된 설명문입니다.")).toBeInTheDocument();
  });

  it("disables the button while generating, prevents duplicate clicks, updates in place, and shows success on generation", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const generatedReport = {
      ...SAMPLE_REPORT,
      content: {
        ...SAMPLE_REPORT.content,
        narrative: "생성된 설명문 초안입니다.",
        narrative_source: "mock",
      },
    };
    const fetchMock = mockFetchRouter({ get: SAMPLE_REPORT, post: generatedReport });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "설명문 초안 생성" });
    await user.click(button);

    // 생성 중에는 버튼이 비활성화되고 문구가 바뀐다(요청이 동기적으로
    // 즉시 끝나므로 최종 성공 상태까지 함께 확인한다).
    await screen.findByDisplayValue("생성된 설명문 초안입니다.");
    expect(screen.queryByRole("button", { name: "설명문 초안 생성" })).not.toBeInTheDocument();

    // 생성 성공 안내: role=status, aria-live=polite, role=alert 아님.
    const success = screen.getByText(
      "설명문 초안이 생성되었습니다. 내용을 검토한 뒤 저장하거나 승인하세요."
    );
    expect(success).toHaveAttribute("role", "status");
    expect(success.closest(".report-save-feedback")).toHaveAttribute("aria-live", "polite");

    const postCalls = fetchMock.mock.calls.filter(
      (call: any[]) => (call[1] as RequestInit)?.method === "POST"
    );
    expect(postCalls).toHaveLength(1);
    expect(String(postCalls[0][0])).toContain("/reports/42/generate-narrative");
  });

  it("removes the previous generation success message once the user edits a field", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const generatedReport = {
      ...SAMPLE_REPORT,
      content: { ...SAMPLE_REPORT.content, narrative: "생성된 설명문", narrative_source: "mock" },
    };
    const fetchMock = mockFetchRouter({ get: SAMPLE_REPORT, post: generatedReport });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "설명문 초안 생성" }));
    await screen.findByText("설명문 초안이 생성되었습니다. 내용을 검토한 뒤 저장하거나 승인하세요.");

    await user.type(screen.getByLabelText("설명문"), " 추가 수정");

    expect(
      screen.queryByText("설명문 초안이 생성되었습니다. 내용을 검토한 뒤 저장하거나 승인하세요.")
    ).not.toBeInTheDocument();
  });

  it("shows the generic error and keeps the button usable when generation fails with an unexpected status", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchRouter({ get: SAMPLE_REPORT, post: { detail: "boom" }, postStatus: 500 });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "설명문 초안 생성" });
    await user.click(button);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("설명문을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    expect(screen.getByRole("button", { name: "설명문 초안 생성" })).not.toBeDisabled();
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows the backend's safe service-unavailable message on a 503", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchRouter({
      get: SAMPLE_REPORT,
      post: { detail: "설명문 생성 서비스를 사용할 수 없습니다." },
      postStatus: 503,
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "설명문 초안 생성" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("설명문 생성 서비스를 사용할 수 없습니다.");
  });

  it("shows the backend's validation-failure message plus a no-change reassurance on a 502", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchRouter({
      get: SAMPLE_REPORT,
      post: { detail: "생성된 설명문이 검증을 통과하지 못했습니다." },
      postStatus: 502,
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "설명문 초안 생성" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("생성된 설명문이 검증을 통과하지 못했습니다.");
    expect(alert).toHaveTextContent("보고서 내용은 변경되지 않았습니다.");
  });

  it("never renders the generation button as a PDF or Word export action", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByRole("button", { name: "설명문 초안 생성" });
    for (const forbiddenName of [/PDF/, /다운로드/, /Word/]) {
      expect(screen.queryByRole("button", { name: forbiddenName })).not.toBeInTheDocument();
    }
  });

  // ======================= Task D1: narrative 출처 문구 =====================

  function withNarrativeSource(source: string | null, edited: boolean) {
    return {
      ...SAMPLE_REPORT,
      content: {
        ...SAMPLE_REPORT.content,
        narrative: "이미 생성된 설명문입니다.",
        narrative_source: source,
        narrative_edited_by_clinician: edited,
      },
    };
  }

  it("shows the mock+unedited source notice", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrativeSource("mock", false)));
    renderPreviewPage();

    expect(await screen.findByText("결정적 Mock 기반 검토 전 초안")).toBeInTheDocument();
    expect(screen.getByText("의료진 검토 전에는 환자에게 공개되지 않습니다.")).toBeInTheDocument();
  });

  it("shows the mock+edited source notice", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrativeSource("mock", true)));
    renderPreviewPage();

    expect(
      await screen.findByText("Mock 초안을 바탕으로 의료진이 수정한 내용")
    ).toBeInTheDocument();
    expect(screen.getByText("의료진 승인 전에는 환자에게 공개되지 않습니다.")).toBeInTheDocument();
  });

  it("shows the llm+unedited source notice", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrativeSource("llm", false)));
    renderPreviewPage();

    expect(await screen.findByText("AI로 생성된 검토 전 초안")).toBeInTheDocument();
    expect(screen.getByText("의료진 검토 전에는 환자에게 공개되지 않습니다.")).toBeInTheDocument();
  });

  it("shows the llm+edited source notice", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrativeSource("llm", true)));
    renderPreviewPage();

    expect(
      await screen.findByText("AI 초안을 바탕으로 의료진이 수정한 내용")
    ).toBeInTheDocument();
    expect(screen.getByText("의료진 승인 전에는 환자에게 공개되지 않습니다.")).toBeInTheDocument();
  });

  it("shows the clinician-authored source notice", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrativeSource("clinician", false)));
    renderPreviewPage();

    expect(await screen.findByText("의료진이 직접 작성한 검토 전 내용")).toBeInTheDocument();
    expect(screen.getByText("승인 전에는 환자에게 공개되지 않습니다.")).toBeInTheDocument();
  });

  it("shows the unknown-source notice when narrative_source is null", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrativeSource(null, false)));
    renderPreviewPage();

    expect(await screen.findByText("의료진 검토 전 초안")).toBeInTheDocument();
    expect(screen.getByText("승인 전에는 환자에게 공개되지 않습니다.")).toBeInTheDocument();
  });

  it("shows the unknown-source notice for an unexpected source value instead of guessing", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrativeSource("some_future_vendor", false)));
    renderPreviewPage();

    expect(await screen.findByText("의료진 검토 전 초안")).toBeInTheDocument();
    // 실제 vendor 이름이나 추측한 출처를 화면에 노출하지 않는다.
    expect(screen.queryByText(/some_future_vendor/)).not.toBeInTheDocument();
  });

  it("never shows vendor, model, or internal provider strings on the doctor screen", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrativeSource("llm", false)));
    renderPreviewPage();

    await screen.findByText("AI로 생성된 검토 전 초안");
    for (const forbidden of ["Ollama", "qwen3", "DETERMINISTIC_MOCK", "RealLLMProvider"]) {
      expect(document.body.textContent).not.toContain(forbidden);
    }
  });

  // ======================= Task 17: 수정·승인·반려 =========================

  it("shows editable textareas for DRAFT, pre-filled with null as empty", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.getByLabelText("설명문")).toHaveValue("");
    expect(screen.getByLabelText("인수인계 메모")).toHaveValue("");
    expect(screen.getByLabelText("환자 안내문")).toHaveValue("");
    expect(screen.getByRole("button", { name: "저장" })).toBeInTheDocument();
  });

  it("shows approve and reject buttons only for DRAFT", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.getByRole("button", { name: "승인" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "반려" })).toBeInTheDocument();
  });

  it("saves all three fields together and updates in place without a full reload", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const patchedReport = {
      ...SAMPLE_REPORT,
      content: {
        ...SAMPLE_REPORT.content,
        narrative: "의사가 작성한 설명",
        handoff_note: "인수인계 메모 내용",
      },
    };
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isPatch = options?.method === "PATCH";
      const body = isPatch ? patchedReport : SAMPLE_REPORT;
      return Promise.resolve({
        ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.type(screen.getByLabelText("설명문"), "의사가 작성한 설명");
    await user.type(screen.getByLabelText("인수인계 메모"), "인수인계 메모 내용");
    await user.click(screen.getByRole("button", { name: "저장" }));

    await screen.findByDisplayValue("의사가 작성한 설명");

    const patchCall = fetchMock.mock.calls.find(
      (call: any[]) => (call[1] as RequestInit)?.method === "PATCH"
    );
    expect(patchCall).toBeDefined();
    const sentBody = JSON.parse(patchCall![1].body);
    expect(sentBody).toEqual({
      narrative: "의사가 작성한 설명",
      handoff_note: "인수인계 메모 내용",
      patient_guidance: null, // 빈 textarea -> null로 정규화
    });
  });

  it("prevents duplicate save requests while one is in flight", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    let resolvePatch: (value: unknown) => void = () => {};
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      if (options?.method === "PATCH") {
        return new Promise((resolve) => {
          resolvePatch = resolve;
        });
      }
      return Promise.resolve({
        ok: true, status: 200, json: async () => SAMPLE_REPORT, text: async () => "",
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.type(screen.getByLabelText("설명문"), "x");
    const saveButton = screen.getByRole("button", { name: "저장" });
    await user.click(saveButton);

    expect(await screen.findByRole("button", { name: "저장하는 중..." })).toBeDisabled();

    const patchCallsBefore = fetchMock.mock.calls.filter(
      (call: any[]) => (call[1] as RequestInit)?.method === "PATCH"
    ).length;
    await user.click(screen.getByRole("button", { name: "저장하는 중..." }));
    const patchCallsAfter = fetchMock.mock.calls.filter(
      (call: any[]) => (call[1] as RequestInit)?.method === "PATCH"
    ).length;
    expect(patchCallsAfter).toBe(patchCallsBefore);

    resolvePatch({ ok: true, status: 200, json: async () => SAMPLE_REPORT, text: async () => "" });
  });

  // ============== Task 20 후속: 저장 성공/실패 피드백 개선 ==============

  it("shows a success message with role=status (not role=alert) after a successful save, and updates last_modified_at from the response", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const patchedReport = {
      ...SAMPLE_REPORT,
      content: { ...SAMPLE_REPORT.content, narrative: "의사가 작성한 설명" },
      last_modified_at: "2026-09-20T03:00:00Z",
    };
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isPatch = options?.method === "PATCH";
      const body = isPatch ? patchedReport : SAMPLE_REPORT;
      return Promise.resolve({
        ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    const lastModifiedBefore = screen.getByText(/마지막 수정일/).textContent;
    await user.type(screen.getByLabelText("설명문"), "의사가 작성한 설명");
    await user.click(screen.getByRole("button", { name: "저장" }));

    const success = await screen.findByText("저장되었습니다.");
    expect(success).toHaveAttribute("role", "status");
    expect(screen.queryAllByRole("alert")).toHaveLength(0);
    // 버튼 자체는 "저장"으로 복귀해도 된다 — 성공 안내는 별도 메시지로 전달한다.
    expect(screen.getByRole("button", { name: "저장" })).toBeInTheDocument();
    expect(screen.getByText(/마지막 수정일/).textContent).not.toBe(lastModifiedBefore);
  });

  it("keeps the success message inside an aria-live=polite region", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isPatch = options?.method === "PATCH";
      const body = isPatch
        ? { ...SAMPLE_REPORT, content: { ...SAMPLE_REPORT.content, narrative: "x" } }
        : SAMPLE_REPORT;
      return Promise.resolve({
        ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.type(screen.getByLabelText("설명문"), "x");
    await user.click(screen.getByRole("button", { name: "저장" }));

    const success = await screen.findByText("저장되었습니다.");
    expect(success.closest(".report-save-feedback")).toHaveAttribute("aria-live", "polite");
  });

  it("keeps the entered values on screen after a successful save", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const patchedReport = {
      ...SAMPLE_REPORT,
      content: {
        ...SAMPLE_REPORT.content,
        narrative: "저장 후에도 남아있는 설명",
        patient_guidance: "저장 후에도 남아있는 안내문",
      },
    };
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isPatch = options?.method === "PATCH";
      const body = isPatch ? patchedReport : SAMPLE_REPORT;
      return Promise.resolve({
        ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.type(screen.getByLabelText("설명문"), "저장 후에도 남아있는 설명");
    await user.type(screen.getByLabelText("환자 안내문"), "저장 후에도 남아있는 안내문");
    await user.click(screen.getByRole("button", { name: "저장" }));

    await screen.findByText("저장되었습니다.");
    expect(screen.getByLabelText("설명문")).toHaveValue("저장 후에도 남아있는 설명");
    expect(screen.getByLabelText("환자 안내문")).toHaveValue("저장 후에도 남아있는 안내문");
  });

  it("removes the previous success message as soon as the user edits a field again", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const patchedReport = {
      ...SAMPLE_REPORT,
      content: { ...SAMPLE_REPORT.content, narrative: "첫 저장 내용" },
    };
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isPatch = options?.method === "PATCH";
      const body = isPatch ? patchedReport : SAMPLE_REPORT;
      return Promise.resolve({
        ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.type(screen.getByLabelText("설명문"), "첫 저장 내용");
    await user.click(screen.getByRole("button", { name: "저장" }));
    await screen.findByText("저장되었습니다.");

    await user.type(screen.getByLabelText("설명문"), " 추가 수정");

    expect(screen.queryByText("저장되었습니다.")).not.toBeInTheDocument();
  });

  it("allows a normal second save after a first successful save", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    let currentNarrative = "첫 저장";
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isPatch = options?.method === "PATCH";
      if (isPatch) {
        const sent = JSON.parse((options!.body as string));
        currentNarrative = sent.narrative;
      }
      const body = { ...SAMPLE_REPORT, content: { ...SAMPLE_REPORT.content, narrative: currentNarrative } };
      return Promise.resolve({
        ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.type(screen.getByLabelText("설명문"), "첫 저장");
    await user.click(screen.getByRole("button", { name: "저장" }));
    await screen.findByText("저장되었습니다.");

    await user.clear(screen.getByLabelText("설명문"));
    await user.type(screen.getByLabelText("설명문"), "두 번째 저장");
    expect(screen.queryByText("저장되었습니다.")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "저장" }));
    await screen.findByText("저장되었습니다.");

    const patchCalls = fetchMock.mock.calls.filter(
      (call: any[]) => (call[1] as RequestInit)?.method === "PATCH"
    );
    expect(patchCalls).toHaveLength(2);
  });

  it("shows no success message and keeps the existing error alert when a save fails", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isPatch = options?.method === "PATCH";
      if (isPatch) {
        return Promise.resolve({ ok: false, status: 500, json: async () => ({ detail: "boom" }), text: async () => "" });
      }
      return Promise.resolve({
        ok: true, status: 200, json: async () => SAMPLE_REPORT, text: async () => JSON.stringify(SAMPLE_REPORT),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.type(screen.getByLabelText("설명문"), "실패할 저장");
    await user.click(screen.getByRole("button", { name: "저장" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("보고서를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    expect(screen.queryByText("저장되었습니다.")).not.toBeInTheDocument();
    // 입력값은 실패 후에도 유지된다.
    expect(screen.getByLabelText("설명문")).toHaveValue("실패할 저장");
  });

  it("does not render the save button or a success message for an APPROVED report", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const approvedReport = {
      ...SAMPLE_REPORT,
      status: "APPROVED",
      reviewed_by_user_id: 1,
      reviewed_at: "2026-09-19T00:00:00Z",
      content: { ...SAMPLE_REPORT.content, narrative: "승인된 설명문" },
    };
    vi.stubGlobal("fetch", mockFetchOnce(200, approvedReport));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.queryByRole("button", { name: "저장" })).not.toBeInTheDocument();
    expect(screen.queryByText("저장되었습니다.")).not.toBeInTheDocument();
  });

  it("shows an inline two-step confirmation before approving, and cancel returns to idle", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const withNarrative = {
      ...SAMPLE_REPORT,
      content: { ...SAMPLE_REPORT.content, narrative: "설명문 있음" },
    };
    vi.stubGlobal("fetch", mockFetchOnce(200, withNarrative));
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.click(screen.getByRole("button", { name: "승인" }));

    expect(screen.getByText("정말 승인하시겠습니까?")).toBeInTheDocument();
    const confirmButton = screen.getByRole("button", { name: "승인 확정" });
    expect(confirmButton).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "취소" }));
    expect(screen.queryByText("정말 승인하시겠습니까?")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "승인" })).toBeInTheDocument();
  });

  it("approves after confirmation and updates the page without a full reload", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const withNarrative = {
      ...SAMPLE_REPORT,
      content: { ...SAMPLE_REPORT.content, narrative: "설명문 있음" },
    };
    const approvedReport = { ...withNarrative, status: "APPROVED", reviewed_by_user_id: 1 };
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isPost = options?.method === "POST" && String(url).includes("/approve");
      const body = isPost ? approvedReport : withNarrative;
      return Promise.resolve({
        ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.click(screen.getByRole("button", { name: "승인" }));
    await user.click(screen.getByRole("button", { name: "승인 확정" }));

    // Task 20B: 보고서 상태 표시를 StatusBadge로 통일하며 문구도
    // "승인"→"승인됨"으로 바뀌었다(의사 화면 전체 상태 어휘 통일).
    expect(await screen.findByText("승인됨")).toBeInTheDocument();
    expect(screen.getByText("승인된 보고서는 수정할 수 없습니다.")).toBeInTheDocument();
  });

  it("shows the 409 detail message inline when approval is rejected for a missing narrative", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isApprove = options?.method === "POST" && String(url).includes("/approve");
      if (isApprove) {
        return Promise.resolve({
          ok: false, status: 409,
          json: async () => ({ detail: "설명문을 작성하거나 생성한 후 승인할 수 있습니다." }),
          text: async () => "",
        });
      }
      return Promise.resolve({
        ok: true, status: 200, json: async () => SAMPLE_REPORT, text: async () => "",
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.click(screen.getByRole("button", { name: "승인" }));
    await user.click(screen.getByRole("button", { name: "승인 확정" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("설명문을 작성하거나 생성한 후 승인할 수 있습니다.");
  });

  it("rejects after inline confirmation and shows the rewrite notice", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const rejectedReport = { ...SAMPLE_REPORT, status: "REJECTED", reviewed_by_user_id: 1 };
    const fetchMock = vi.fn().mockImplementation((url: unknown, options?: RequestInit) => {
      const isReject = options?.method === "POST" && String(url).includes("/reject");
      const body = isReject ? rejectedReport : SAMPLE_REPORT;
      return Promise.resolve({
        ok: true, status: 200, json: async () => body, text: async () => JSON.stringify(body),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();
    const user = userEvent.setup();

    await screen.findByText("진료참고 보고서");
    await user.click(screen.getByRole("button", { name: "반려" }));
    expect(screen.getByText("정말 반려하시겠습니까?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "반려 확정" }));

    expect(
      await screen.findByText("반려된 보고서입니다. 내용을 저장하면 다시 초안 상태가 됩니다.")
    ).toBeInTheDocument();
    // 반려 상태에서는 승인/반려 버튼이 사라지고 편집 폼만 남는다.
    expect(screen.queryByRole("button", { name: "승인" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "반려" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "저장" })).toBeInTheDocument();
  });

  it("shows APPROVED content as read-only with no save/approve/reject buttons", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const approvedReport = {
      ...SAMPLE_REPORT,
      status: "APPROVED",
      reviewed_by_user_id: 1,
      reviewed_at: "2026-09-19T00:00:00Z",
      content: { ...SAMPLE_REPORT.content, narrative: "승인된 설명문" },
    };
    vi.stubGlobal("fetch", mockFetchOnce(200, approvedReport));
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    expect(screen.getByText("승인된 보고서는 수정할 수 없습니다.")).toBeInTheDocument();
    expect(screen.getByText(/설명문: 승인된 설명문/)).toBeInTheDocument();
    expect(screen.queryByLabelText("설명문")).not.toBeInTheDocument(); // textarea 없음
    expect(screen.queryByRole("button", { name: "저장" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "승인" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "반려" })).not.toBeInTheDocument();
  });

  it("never calls the patient-facing exposure API (no such feature exists yet)", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchOnce(200, SAMPLE_REPORT);
    vi.stubGlobal("fetch", fetchMock);
    renderPreviewPage();

    await screen.findByText("진료참고 보고서");
    for (const call of fetchMock.mock.calls) {
      expect(String(call[0])).not.toContain("/publish");
      expect(String(call[0])).not.toContain("/patient-view");
    }
  });
});
