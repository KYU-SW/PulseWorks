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

const EMPTY_LAB_TRENDS = { patient: SAMPLE_TIMELINE.patient, trends: [] };

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

// PatientTimelinePage는 /timeline과 /lab-trends 두 엔드포인트를 함께 호출하므로,
// URL에 따라 다른 응답을 주도록 라우팅한다 — 하나의 고정 응답만 주면
// LabTrendSection이 타임라인 바디를 받아 깨진 상태로 렌더링된다.
function mockFetchRouter(
  routes: Record<string, { status: number; body: unknown }>,
  fallback: { status: number; body: unknown } = { status: 200, body: EMPTY_LAB_TRENDS }
) {
  return vi.fn().mockImplementation((url: unknown) => {
    const path = String(url);
    const match = Object.keys(routes).find((key) => path.includes(key));
    const { status, body } = match ? routes[match] : fallback;
    return Promise.resolve({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
      text: async () => JSON.stringify(body),
    });
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
          <Route path="/doctor/reports/:reportId" element={<div>REPORT_PREVIEW_SCREEN</div>} />
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
    vi.stubGlobal("fetch", mockFetchRouter({ "/timeline": { status: 200, body: SAMPLE_TIMELINE } }));
    renderTimelinePage();

    expect(await screen.findByText("합성환자-내분비01")).toBeInTheDocument();
    expect(screen.getByText(/SYN-0001/)).toBeInTheDocument();
    expect(screen.getByText(/1968-04-12/)).toBeInTheDocument();
    // LabTrendSection도 자체 합성 데이터 안내문을 갖고 있어 복수 개 존재할 수 있다.
    expect(screen.getAllByText(/합성\(가짜\) 교육용 데이터/).length).toBeGreaterThan(0);
  });

  it("shows Korean labels for each event type and the lab value in the summary", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchRouter({ "/timeline": { status: 200, body: SAMPLE_TIMELINE } }));
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
      mockFetchRouter({
        "/timeline": { status: 200, body: { patient: SAMPLE_TIMELINE.patient, timeline: [] } },
      })
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
    let timelineCallCount = 0;
    const fetchMock = vi.fn().mockImplementation((url: unknown) => {
      const path = String(url);
      if (path.includes("/timeline")) {
        timelineCallCount += 1;
        const body = timelineCallCount === 1 ? { detail: "boom" } : SAMPLE_TIMELINE;
        const status = timelineCallCount === 1 ? 500 : 200;
        return Promise.resolve({
          ok: status < 300,
          status,
          json: async () => body,
          text: async () => JSON.stringify(body),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => EMPTY_LAB_TRENDS,
        text: async () => JSON.stringify(EMPTY_LAB_TRENDS),
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderTimelinePage();
    const user = userEvent.setup();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).not.toContain("boom");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));

    expect(await screen.findByText("합성환자-내분비01")).toBeInTheDocument();
    // 타임라인 실패 + 타임라인 재시도(성공) + 검사 추세 호출 = 3회
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("has a link back to the assigned patient list", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchRouter({ "/timeline": { status: 200, body: SAMPLE_TIMELINE } }));
    renderTimelinePage();

    const backLink = await screen.findByRole("link", { name: /담당 환자 목록으로 돌아가기/ });
    expect(backLink).toHaveAttribute("href", "/doctor");
  });

  it("never logs the token to the console while loading the timeline", async () => {
    const token = makeFakeJwt("DOCTOR");
    setStoredToken(token);
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    vi.stubGlobal("fetch", mockFetchRouter({ "/timeline": { status: 200, body: SAMPLE_TIMELINE } }));
    renderTimelinePage();

    await screen.findByText("합성환자-내분비01");

    for (const call of consoleSpy.mock.calls) {
      expect(call.map(String).join(" ")).not.toContain(token);
    }
    consoleSpy.mockRestore();
  });

  const SAMPLE_REPORT = {
    id: 42, patient_id: 1, encounter_id: 1, report_type: "DOCTOR_REFERENCE",
    scope_type: "SINGLE_ENCOUNTER", scope_encounter_ids: [1], status: "DRAFT",
    content: {
      emr_snapshot: {
        patient: SAMPLE_TIMELINE.patient, encounters: [], diagnoses: [], lab_results: [],
        lab_trends: [], prescriptions: [], allergies: [], safety_alerts: [],
        clinical_notes: [], source_record_ids: [],
      },
      narrative: null, handoff_note: null, patient_guidance: null,
    },
    created_by_user_id: 1, created_at: "2026-09-18T00:00:00Z",
    last_modified_by_user_id: 1, last_modified_at: "2026-09-18T00:00:00Z",
    reviewed_by_user_id: null, reviewed_at: null, supersedes_report_id: null,
  };

  // 9. 각 Encounter에 보고서 생성 버튼 표시
  it("shows a report-generation button for each ENCOUNTER item", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchRouter({ "/timeline": { status: 200, body: SAMPLE_TIMELINE } }));
    renderTimelinePage();

    expect(
      await screen.findByRole("button", { name: "이 방문으로 진료참고 보고서 생성" })
    ).toBeInTheDocument();
  });

  // 10, 11, 12. 버튼 클릭 시 해당 Encounter ID/현재 patientId 사용, 허용 필드만 전송
  it("posts only the allowed fields using the current patientId and the clicked encounter's id", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchRouter({
      "/timeline": { status: 200, body: SAMPLE_TIMELINE },
      "/reports": { status: 201, body: SAMPLE_REPORT },
    });
    vi.stubGlobal("fetch", fetchMock);
    renderTimelinePage("1");
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "이 방문으로 진료참고 보고서 생성" });
    await user.click(button);

    const postCall = fetchMock.mock.calls.find((call: any[]) =>
      String(call[0]).includes("/reports")
    );
    expect(postCall).toBeDefined();
    expect(String(postCall![0])).toContain("/patients/1/reports");
    const body = JSON.parse(postCall![1].body);
    expect(body).toEqual({
      report_type: "DOCTOR_REFERENCE",
      scope_type: "SINGLE_ENCOUNTER",
      encounter_ids: [1], // SAMPLE_TIMELINE의 ENCOUNTER 항목의 encounter_id
    });
    expect(Object.keys(body)).toEqual(["report_type", "scope_type", "encounter_ids"]);
  });

  // 13 & 14. 요청 중 버튼 disabled, 중복 클릭 방지
  it("disables the button while the request is in flight and ignores extra clicks", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    let resolvePost: (value: unknown) => void = () => {};
    const fetchMock = vi.fn().mockImplementation((url: unknown, options: RequestInit) => {
      const path = String(url);
      if (path.includes("/reports") && options?.method === "POST") {
        return new Promise((resolve) => {
          resolvePost = resolve;
        });
      }
      if (path.includes("/timeline")) {
        return Promise.resolve({
          ok: true, status: 200, json: async () => SAMPLE_TIMELINE, text: async () => "",
        });
      }
      return Promise.resolve({
        ok: true, status: 200, json: async () => EMPTY_LAB_TRENDS, text: async () => "",
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    renderTimelinePage();
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "이 방문으로 진료참고 보고서 생성" });
    await user.click(button);

    expect(await screen.findByRole("button", { name: "보고서를 생성하는 중..." })).toBeDisabled();

    const postCallsBeforeSecondClick = fetchMock.mock.calls.filter((call: any[]) =>
      String(call[0]).includes("/reports")
    ).length;
    await user.click(screen.getByRole("button", { name: "보고서를 생성하는 중..." }));
    const postCallsAfterSecondClick = fetchMock.mock.calls.filter((call: any[]) =>
      String(call[0]).includes("/reports")
    ).length;
    expect(postCallsAfterSecondClick).toBe(postCallsBeforeSecondClick); // 추가 호출 없음

    resolvePost({ ok: true, status: 201, json: async () => SAMPLE_REPORT, text: async () => "" });
  });

  // 15. 201 성공 시 보고서 페이지 이동
  it("navigates to the report preview page on a 201 response", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchRouter({
        "/timeline": { status: 200, body: SAMPLE_TIMELINE },
        "/reports": { status: 201, body: SAMPLE_REPORT },
      })
    );
    renderTimelinePage();
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "이 방문으로 진료참고 보고서 생성" });
    await user.click(button);

    expect(await screen.findByText("REPORT_PREVIEW_SCREEN")).toBeInTheDocument();
  });

  // 16. 200 성공 시 같은 방식으로 이동
  it("navigates to the report preview page on a 200 (reused DRAFT) response the same way", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchRouter({
        "/timeline": { status: 200, body: SAMPLE_TIMELINE },
        "/reports": { status: 200, body: SAMPLE_REPORT },
      })
    );
    renderTimelinePage();
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "이 방문으로 진료참고 보고서 생성" });
    await user.click(button);

    expect(await screen.findByText("REPORT_PREVIEW_SCREEN")).toBeInTheDocument();
  });

  // 17 & 18. 생성 실패 시 일반 오류 안내, 실패 후 버튼 다시 사용 가능
  it("shows a generic error and re-enables the button when report creation fails", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchRouter({
        "/timeline": { status: 200, body: SAMPLE_TIMELINE },
        "/reports": { status: 500, body: { detail: "boom" } },
      })
    );
    renderTimelinePage();
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "이 방문으로 진료참고 보고서 생성" });
    await user.click(button);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("보고서를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    expect(
      screen.getByRole("button", { name: "이 방문으로 진료참고 보고서 생성" })
    ).not.toBeDisabled();
  });

  // 19. 401 전역 로그인 이동 유지
  it("follows the existing global 401 flow when report creation returns 401", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchRouter({
        "/timeline": { status: 200, body: SAMPLE_TIMELINE },
        "/reports": { status: 401, body: { detail: "Invalid token" } },
      })
    );
    renderTimelinePage();
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "이 방문으로 진료참고 보고서 생성" });
    await user.click(button);

    await waitFor(() => expect(screen.getByText("LOGIN_SCREEN")).toBeInTheDocument());
  });

  // 20. 다른 환자 ID를 요청하지 않음
  it("only ever requests the current page's patientId, never another one", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchRouter({
      "/timeline": { status: 200, body: SAMPLE_TIMELINE },
      "/reports": { status: 201, body: SAMPLE_REPORT },
    });
    vi.stubGlobal("fetch", fetchMock);
    renderTimelinePage("7");
    const user = userEvent.setup();

    const button = await screen.findByRole("button", { name: "이 방문으로 진료참고 보고서 생성" });
    await user.click(button);

    const postCall = fetchMock.mock.calls.find((call: any[]) =>
      String(call[0]).includes("/reports")
    );
    expect(postCall).toBeDefined();
    expect(String(postCall![0])).toContain("/patients/7/reports");
    expect(String(postCall![0])).not.toContain("/patients/1/reports");
  });

  // ======================= Task F4-A: VitalSign =======================

  const TIMELINE_WITH_VITAL_SIGNS = {
    patient: SAMPLE_TIMELINE.patient,
    timeline: [
      ...SAMPLE_TIMELINE.timeline,
      {
        id: 10,
        encounter_id: 1,
        event_type: "VITAL_SIGN",
        event_time: "2026-03-10T09:00:00+00:00",
        title: "혈압",
        summary: "120.000/80.000 mmHg",
        source_type: "INSTITUTION_GENERATED",
        department: "내분비내과",
        vital_type: "BLOOD_PRESSURE",
        value: "120.000",
        value_secondary: "80.000",
        unit: "mmHg",
        quality_warnings: [],
        bmi: null,
      },
      {
        id: 11,
        encounter_id: 1,
        event_type: "VITAL_SIGN",
        event_time: "2026-03-10T09:00:00+00:00",
        title: "체온",
        summary: "36.500 Cel",
        source_type: "INSTITUTION_GENERATED",
        department: "내분비내과",
        vital_type: "BODY_TEMPERATURE",
        value: "36.500",
        value_secondary: null,
        unit: "Cel",
        quality_warnings: ["수축기 값이 이완기 값보다 낮습니다."],
        bmi: null,
      },
    ],
  };

  it("shows the Korean label and rounded value+unit for a VITAL_SIGN item", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchRouter({ "/timeline": { status: 200, body: TIMELINE_WITH_VITAL_SIGNS } })
    );
    renderTimelinePage();

    await screen.findByText("합성환자-내분비01");
    // 활력징후 항목이 2건(혈압·체온)이라 라벨도 2번 나온다.
    expect(screen.getAllByText("활력징후").length).toBe(2);
    expect(screen.getByText("120/80 mmHg")).toBeInTheDocument(); // 원본 "120.000/80.000"이 반올림됨
    expect(screen.getByText("36.5℃")).toBeInTheDocument();
  });

  it("shows a quality warning only for the VITAL_SIGN item that has one", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchRouter({ "/timeline": { status: 200, body: TIMELINE_WITH_VITAL_SIGNS } })
    );
    renderTimelinePage();

    const warning = await screen.findByText("수축기 값이 이완기 값보다 낮습니다.");
    expect(warning.closest('[role="alert"]') ?? warning).toBeInTheDocument();
    // 정상 혈압(경고 없음) 항목에는 경고 문구가 붙지 않는다 — 전체
    // 경고 문구 개수가 1개뿐이어야 한다.
    expect(screen.getAllByText("수축기 값이 이완기 값보다 낮습니다.")).toHaveLength(1);
  });

  it("shows BMI next to the ENCOUNTER item when the backend provides it", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const timelineWithBmi = {
      patient: SAMPLE_TIMELINE.patient,
      timeline: SAMPLE_TIMELINE.timeline.map((item) =>
        item.event_type === "ENCOUNTER" ? { ...item, bmi: "22.5" } : item
      ),
    };
    vi.stubGlobal(
      "fetch",
      mockFetchRouter({ "/timeline": { status: 200, body: timelineWithBmi } })
    );
    renderTimelinePage();

    expect(await screen.findByText(/BMI 22\.5/)).toBeInTheDocument();
  });

  it("does not show a BMI line when the backend does not provide one", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchRouter({ "/timeline": { status: 200, body: SAMPLE_TIMELINE } }));
    renderTimelinePage();

    await screen.findByText("합성환자-내분비01");
    expect(screen.queryByText(/BMI/)).not.toBeInTheDocument();
  });

  it("still renders existing event types unchanged when the response has no vital signs", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchRouter({ "/timeline": { status: 200, body: SAMPLE_TIMELINE } }));
    renderTimelinePage();

    await screen.findByText("합성환자-내분비01");
    expect(screen.getByText("검사결과")).toBeInTheDocument();
    expect(screen.getByText(/8\.1%/)).toBeInTheDocument();
  });
});
