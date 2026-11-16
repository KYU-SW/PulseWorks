import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import { setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import ProtectedRoute from "../routes/ProtectedRoute";
import DoctorReportsPage from "./DoctorReportsPage";

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

function makeItem(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: 1,
    patient_id: 1,
    patient_name: "합성환자-내분비01",
    patient_mrn: "SYN-0001",
    encounter_id: 10,
    report_type: "DOCTOR_REFERENCE",
    scope_type: "SINGLE_ENCOUNTER",
    status: "DRAFT",
    created_at: "2026-01-01T00:00:00Z",
    reviewed_at: null,
    ...overrides,
  };
}

function makeListResponse(items: unknown[], overrides: Partial<Record<string, unknown>> = {}) {
  return {
    items,
    total: items.length,
    page: 1,
    page_size: 20,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={["/doctor/reports"]}>
        <Routes>
          <Route
            path="/doctor/reports"
            element={
              <ProtectedRoute allowedRoles={["DOCTOR"]}>
                <DoctorReportsPage />
              </ProtectedRoute>
            }
          />
          <Route path="/doctor/reports/:reportId" element={<div>REPORT_DETAIL</div>} />
          <Route path="/login" element={<div>LOGIN_SCREEN</div>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>
  );
}

describe("DoctorReportsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  // 1. report table 렌더링 + 2. StatusBadge 표시 + 3. 보기 링크
  it("renders the report table with a status badge and a view link", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, makeListResponse([makeItem()])));
    renderPage();

    const table = await screen.findByRole("table");
    expect(within(table).getByText("합성환자-내분비01 (SYN-0001)")).toBeInTheDocument();
    expect(within(table).getByText("초안")).toBeInTheDocument();
    expect(within(table).getByRole("link", { name: "보기" })).toHaveAttribute(
      "href",
      "/doctor/reports/1"
    );
  });

  // 4. status filter → API parameter
  it("sends the selected status as a query parameter", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchOnce(200, makeListResponse([makeItem()]));
    vi.stubGlobal("fetch", fetchMock);
    renderPage();
    const user = userEvent.setup();

    await screen.findByRole("table");
    await user.selectOptions(screen.getByLabelText("상태"), "APPROVED");

    await waitFor(() => {
      const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
      expect(String(lastCall[0])).toContain("status=APPROVED");
    });
  });

  // 5. from/to → API parameter
  it("sends from_date and to_date as query parameters", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = mockFetchOnce(200, makeListResponse([makeItem()]));
    vi.stubGlobal("fetch", fetchMock);
    renderPage();
    const user = userEvent.setup();

    await screen.findByRole("table");
    await user.type(screen.getByLabelText("시작일"), "2026-01-01");
    await user.type(screen.getByLabelText("종료일"), "2026-01-31");

    await waitFor(() => {
      const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
      expect(String(lastCall[0])).toContain("from_date=2026-01-01");
      expect(String(lastCall[0])).toContain("to_date=2026-01-31");
    });
  });

  // 6. filter result loading
  it("shows a loading state while refetching after a filter change", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => makeListResponse([makeItem()]),
      text: async () => "",
    });
    vi.stubGlobal("fetch", fetchMock);
    renderPage();
    const user = userEvent.setup();

    await screen.findByRole("table");
    // 두 번째 호출(필터 변경 후)은 응답을 영원히 보류시켜 로딩 상태를
    // 안정적으로 관찰한다.
    fetchMock.mockImplementation(() => new Promise(() => {}));
    await user.selectOptions(screen.getByLabelText("상태"), "APPROVED");

    expect(screen.getByText("진료 보고서 목록을 불러오는 중...")).toBeInTheDocument();
  });

  // 7. empty result (전체 비어있음)
  it("shows a factual empty message when there are no reports at all", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, makeListResponse([])));
    renderPage();

    await screen.findByText("조회할 진료 보고서가 없습니다.");
  });

  // 7b. empty result (필터 결과 없음 - 구분된 문구)
  it("shows a distinct empty message when a filter yields no results", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => makeListResponse([makeItem()]),
        text: async () => "",
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => makeListResponse([]),
        text: async () => "",
      });
    vi.stubGlobal("fetch", fetchMock);
    renderPage();
    const user = userEvent.setup();

    await screen.findByRole("table");
    await user.selectOptions(screen.getByLabelText("상태"), "REJECTED");

    await screen.findByText("조건에 맞는 진료 보고서가 없습니다.");
  });

  // 8. API error
  it("shows an error state with retry when the API call fails", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({ detail: "서버 오류" }),
        text: async () => "",
      })
    );
    renderPage();

    await screen.findByRole("alert");
  });

  // 9/10/11/12. pagination
  it("paginates with previous/next, disabling at the first and last page", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: async () =>
          makeListResponse([makeItem({ id: 1 })], { total: 25, page: 1, page_size: 20 }),
        text: async () => "",
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    renderPage();
    const user = userEvent.setup();

    await screen.findByRole("table");
    expect(screen.getByRole("button", { name: "이전" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "다음" })).toBeEnabled();

    fetchMock.mockImplementation(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: async () =>
          makeListResponse([makeItem({ id: 2 })], { total: 25, page: 2, page_size: 20 }),
        text: async () => "",
      })
    );
    await user.click(screen.getByRole("button", { name: "다음" }));

    await waitFor(() => {
      const lastCall = fetchMock.mock.calls[fetchMock.mock.calls.length - 1];
      expect(String(lastCall[0])).toContain("page=2");
    });
    await waitFor(() => expect(screen.getByRole("button", { name: "다음" })).toBeDisabled());
    expect(screen.getByRole("button", { name: "이전" })).toBeEnabled();
  });

  // 13. narrative/content가 list UI에 직접 노출되지 않음
  it("never renders report narrative or content in the list", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal(
      "fetch",
      mockFetchOnce(
        200,
        makeListResponse([
          makeItem({ narrative: "이 텍스트는 응답에 없어야 하며, 있어도 렌더링되면 안 된다." }),
        ])
      )
    );
    renderPage();

    await screen.findByRole("table");
    expect(
      screen.queryByText("이 텍스트는 응답에 없어야 하며, 있어도 렌더링되면 안 된다.")
    ).not.toBeInTheDocument();
  });
});
