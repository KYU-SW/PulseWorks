import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import PatientReportsPage from "./PatientReportsPage";

const SAMPLE_LIST = [
  {
    id: 1,
    report_type: "DOCTOR_REFERENCE",
    department: "ENDOCRINOLOGY",
    encounter_date: "2026-03-10",
    reviewed_at: "2026-03-11T00:00:00Z",
  },
];

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

function renderPage() {
  return render(
    <MemoryRouter>
      <PatientReportsPage />
    </MemoryRouter>
  );
}

describe("PatientReportsPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  it("shows a loading state before the list resolves", () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_LIST));
    renderPage();

    expect(screen.getByText("보고서 목록을 불러오는 중...")).toBeInTheDocument();
  });

  it("shows each approved report as a link to its detail page", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_LIST));
    renderPage();

    const link = await screen.findByRole("link", { name: /내분비내과/ });
    expect(link).toHaveAttribute("href", "/patient/reports/1");
  });

  it("shows an empty state as normal, not an error, when there are no approved reports", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, []));
    renderPage();

    expect(await screen.findByText("현재 확인할 수 있는 승인 보고서가 없습니다.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a forbidden message on 403", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(403, { detail: "Forbidden for this role" }));
    renderPage();

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("보고서 목록을 조회할 권한이 없습니다.");
  });

  it("shows a generic error with a working retry button on a server error", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ detail: "boom" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => SAMPLE_LIST });
    vi.stubGlobal("fetch", fetchMock);
    renderPage();
    const user = userEvent.setup();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).not.toContain("boom");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));

    await waitFor(() => expect(screen.getByRole("link")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("redirects nowhere itself on 401 but leaves handling to client.ts (no crash)", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(401, { detail: "Invalid token" }));
    renderPage();

    await waitFor(() => expect(screen.getByText("보고서 목록을 불러오는 중...")).toBeInTheDocument());
  });
});
