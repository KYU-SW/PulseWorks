import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import LabTrendSection from "./LabTrendSection";

const MULTI_POINT_TRENDS = {
  patient: { id: 1, mrn: "SYN-0001", name: "합성환자-내분비01", birth_date: "1968-04-12" },
  trends: [
    {
      test_name: "HbA1c",
      unit: "%",
      points: [
        {
          value: 7.2, unit: "%", reference_low: 4.0, reference_high: 6.0,
          measured_at: "2026-03-10T09:00:00+00:00", status: "HIGH",
          rule_id: "LAB_REFERENCE_RANGE", encounter_id: 1, source_type: "INSTITUTION_GENERATED",
        },
        {
          value: 7.8, unit: "%", reference_low: 4.0, reference_high: 6.0,
          measured_at: "2026-06-10T09:00:00+00:00", status: "HIGH",
          rule_id: "LAB_REFERENCE_RANGE", encounter_id: 2, source_type: "INSTITUTION_GENERATED",
        },
        {
          value: 8.1, unit: "%", reference_low: 4.0, reference_high: 6.0,
          measured_at: "2026-09-05T09:00:00+00:00", status: "HIGH",
          rule_id: "LAB_REFERENCE_RANGE", encounter_id: 3, source_type: "INSTITUTION_GENERATED",
        },
      ],
    },
    {
      test_name: "Fasting Glucose",
      unit: "mg/dL",
      points: [
        {
          value: 130, unit: "mg/dL", reference_low: 70.0, reference_high: 100.0,
          measured_at: "2026-03-10T09:00:00+00:00", status: "HIGH",
          rule_id: "LAB_REFERENCE_RANGE", encounter_id: 1, source_type: "INSTITUTION_GENERATED",
        },
        {
          value: 145, unit: "mg/dL", reference_low: 70.0, reference_high: 100.0,
          measured_at: "2026-06-10T09:00:00+00:00", status: "HIGH",
          rule_id: "LAB_REFERENCE_RANGE", encounter_id: 2, source_type: "INSTITUTION_GENERATED",
        },
      ],
    },
  ],
};

const SINGLE_POINT_TRENDS = {
  patient: { id: 3, mrn: "SYN-0003", name: "합성환자-응급01", birth_date: "1980-01-01" },
  trends: [
    {
      test_name: "Heart Rate",
      unit: "bpm",
      points: [
        {
          value: 118, unit: "bpm", reference_low: 60.0, reference_high: 100.0,
          measured_at: "2026-05-01T10:00:00+00:00", status: "HIGH",
          rule_id: "LAB_REFERENCE_RANGE", encounter_id: 5, source_type: "INSTITUTION_GENERATED",
        },
      ],
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

describe("LabTrendSection", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  it("shows a loading state before the trends resolve", () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, MULTI_POINT_TRENDS));
    render(<LabTrendSection patientId={1} />);

    expect(screen.getByText("검사 추세를 불러오는 중...")).toBeInTheDocument();
  });

  it("defaults to HbA1c and renders a chart + table for 2+ points", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, MULTI_POINT_TRENDS));
    render(<LabTrendSection patientId={1} />);

    expect(await screen.findByRole("img", { name: /검사값 추세 그래프/ })).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("row")).toHaveLength(4); // header + 3 points
    expect(within(table).getByText("7.2")).toBeInTheDocument();
    expect(within(table).getByText("8.1")).toBeInTheDocument();
  });

  it("shows the status as text, not only as color", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, MULTI_POINT_TRENDS));
    render(<LabTrendSection patientId={1} />);

    await screen.findByRole("table");
    expect(screen.getAllByText("높음").length).toBeGreaterThan(0); // HIGH -> 텍스트 라벨
  });

  it("lets the doctor switch between test items via the select", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, MULTI_POINT_TRENDS));
    render(<LabTrendSection patientId={1} />);
    const user = userEvent.setup();

    await screen.findByRole("table");
    const select = screen.getByRole("combobox");
    await user.selectOptions(select, "Fasting Glucose|mg/dL");

    const table = screen.getByRole("table");
    expect(within(table).getByText("130")).toBeInTheDocument();
    expect(within(table).getByText("145")).toBeInTheDocument();
    expect(within(table).queryByText("7.2")).not.toBeInTheDocument();
  });

  it("renders a single-result card instead of a chart when there is exactly one point", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SINGLE_POINT_TRENDS));
    render(<LabTrendSection patientId={3} />);

    expect(await screen.findByText(/측정값 1건/)).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: /검사값 추세 그래프/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("shows an empty state when there are no lab results at all", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, { patient: MULTI_POINT_TRENDS.patient, trends: [] }));
    render(<LabTrendSection patientId={2} />);

    expect(await screen.findByText("표시할 검사결과가 없습니다.")).toBeInTheDocument();
  });

  it("shows a forbidden message on 403 without leaking clinical data", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(403, { detail: "Forbidden for this role" }));
    render(<LabTrendSection patientId={1} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("검사 추세를 조회할 권한이 없습니다.");
    expect(screen.queryByText(/HbA1c/)).not.toBeInTheDocument();
  });

  it("shows a not-found message on 404", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(404, { detail: "환자를 찾을 수 없거나 조회할 수 없습니다." }));
    render(<LabTrendSection patientId={999999} />);

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("환자를 찾을 수 없습니다.");
  });

  it("shows a generic error with a working retry button on a server error", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ detail: "boom" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => MULTI_POINT_TRENDS });
    vi.stubGlobal("fetch", fetchMock);
    render(<LabTrendSection patientId={1} />);
    const user = userEvent.setup();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).not.toContain("boom");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));

    await waitFor(() => expect(screen.getByRole("table")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("redirects nowhere itself on 401 but leaves handling to client.ts (no crash)", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(401, { detail: "Invalid token" }));
    render(<LabTrendSection patientId={1} />);

    await waitFor(() => expect(screen.getByText("검사 추세를 불러오는 중...")).toBeInTheDocument());
  });

  it("always shows the synthetic-data and demo-reference-range disclaimer", async () => {
    setStoredToken(makeFakeJwt("DOCTOR"));
    vi.stubGlobal("fetch", mockFetchOnce(200, MULTI_POINT_TRENDS));
    render(<LabTrendSection patientId={1} />);

    expect(screen.getByText(/합성\(가짜\) 교육용 데이터와 데모 참고범위/)).toBeInTheDocument();
    expect(screen.getByText(/진단이나 예측을 수행하지 않으며/)).toBeInTheDocument();
  });
});
