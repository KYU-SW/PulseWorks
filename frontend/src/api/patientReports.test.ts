import { afterEach, expect, it, vi } from "vitest";
import { setStoredToken } from "./client";
import { makeFakeJwt } from "../test/fakeJwt";
import { getPatientReport, getPatientReports } from "./patientReports";

const SAMPLE_LIST_ITEM = {
  id: 1,
  report_type: "DOCTOR_REFERENCE",
  department: "ENDOCRINOLOGY",
  encounter_date: "2026-03-10",
  reviewed_at: "2026-03-11T00:00:00Z",
};

const SAMPLE_DETAIL = {
  id: 1,
  department: "ENDOCRINOLOGY",
  encounter_type: "OUTPATIENT",
  encounter_date: "2026-03-10",
  reviewed_at: "2026-03-11T00:00:00Z",
  narrative: "승인된 설명문",
  patient_guidance: null,
  diagnoses: [],
  lab_results: [],
  lab_trends: [],
  prescriptions: [],
  allergies: [],
  evidence: [],
  safety_notice: "검사결과와 참고범위만으로 건강상태를 판단하지 마세요.",
};

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

it("gets /patient/reports and returns the list unchanged", async () => {
  setStoredToken(makeFakeJwt("PATIENT"));
  const fetchMock = mockFetchOnce(200, [SAMPLE_LIST_ITEM]);
  vi.stubGlobal("fetch", fetchMock);

  const reports = await getPatientReports();

  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain("/patient/reports");
  expect(options.method).toBe("GET");
  expect(reports).toEqual([SAMPLE_LIST_ITEM]);
});

it("attaches the stored token as a Bearer header via the shared client", async () => {
  const token = makeFakeJwt("PATIENT");
  setStoredToken(token);
  const fetchMock = mockFetchOnce(200, []);
  vi.stubGlobal("fetch", fetchMock);

  await getPatientReports();

  const [, options] = fetchMock.mock.calls[0];
  expect(options.headers.Authorization).toBe(`Bearer ${token}`);
});

it("gets /patient/reports/{report_id} and returns the detail unchanged", async () => {
  setStoredToken(makeFakeJwt("PATIENT"));
  const fetchMock = mockFetchOnce(200, SAMPLE_DETAIL);
  vi.stubGlobal("fetch", fetchMock);

  const report = await getPatientReport(1);

  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain("/patient/reports/1");
  expect(options.method).toBe("GET");
  expect(report).toEqual(SAMPLE_DETAIL);
});

it("never logs the token to the console", async () => {
  const token = makeFakeJwt("PATIENT");
  setStoredToken(token);
  const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
  vi.stubGlobal("fetch", mockFetchOnce(200, []));

  await getPatientReports();

  for (const call of consoleSpy.mock.calls) {
    expect(call.map(String).join(" ")).not.toContain(token);
  }
  consoleSpy.mockRestore();
});
