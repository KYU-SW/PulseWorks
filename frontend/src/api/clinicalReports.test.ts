import { afterEach, expect, it, vi } from "vitest";
import { setStoredToken } from "./client";
import { makeFakeJwt } from "../test/fakeJwt";
import { createClinicalReport, getClinicalReport } from "./clinicalReports";

const SAMPLE_REPORT = {
  id: 1,
  patient_id: 1,
  encounter_id: 1,
  report_type: "DOCTOR_REFERENCE",
  scope_type: "SINGLE_ENCOUNTER",
  scope_encounter_ids: [1],
  status: "DRAFT",
  content: {
    emr_snapshot: {
      patient: { id: 1, mrn: "SYN-0001", name: "합성환자-내분비01", birth_date: "1968-04-12" },
      encounters: [], diagnoses: [], lab_results: [], lab_trends: [], prescriptions: [],
      allergies: [], safety_alerts: [], clinical_notes: [], source_record_ids: [],
    },
    narrative: null, handoff_note: null, patient_guidance: null,
  },
  created_by_user_id: 1,
  created_at: "2026-09-18T00:00:00Z",
  last_modified_by_user_id: 1,
  last_modified_at: "2026-09-18T00:00:00Z",
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

afterEach(() => {
  vi.unstubAllGlobals();
  sessionStorage.clear();
});

// 1 & 2. 올바른 POST URL과 정확한 request body
it("posts to /patients/{patient_id}/reports with the exact request body", async () => {
  setStoredToken(makeFakeJwt("DOCTOR"));
  const fetchMock = mockFetchOnce(201, SAMPLE_REPORT);
  vi.stubGlobal("fetch", fetchMock);

  await createClinicalReport(1, {
    report_type: "DOCTOR_REFERENCE",
    scope_type: "SINGLE_ENCOUNTER",
    encounter_ids: [1],
  });

  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain("/patients/1/reports");
  expect(JSON.parse(options.body)).toEqual({
    report_type: "DOCTOR_REFERENCE",
    scope_type: "SINGLE_ENCOUNTER",
    encounter_ids: [1],
  });
});

// 3. Bearer Token은 기존 client 재사용
it("attaches the stored token as a Bearer header via the shared client", async () => {
  const token = makeFakeJwt("DOCTOR");
  setStoredToken(token);
  const fetchMock = mockFetchOnce(201, SAMPLE_REPORT);
  vi.stubGlobal("fetch", fetchMock);

  await createClinicalReport(1, {
    report_type: "DOCTOR_REFERENCE",
    scope_type: "SINGLE_ENCOUNTER",
    encounter_ids: [1],
  });

  const [, options] = fetchMock.mock.calls[0];
  expect(options.headers.Authorization).toBe(`Bearer ${token}`);
});

// 4. 201 응답 처리
it("returns the created report on a 201 response", async () => {
  setStoredToken(makeFakeJwt("DOCTOR"));
  vi.stubGlobal("fetch", mockFetchOnce(201, SAMPLE_REPORT));

  const report = await createClinicalReport(1, {
    report_type: "DOCTOR_REFERENCE",
    scope_type: "SINGLE_ENCOUNTER",
    encounter_ids: [1],
  });

  expect(report.id).toBe(1);
  expect(report.status).toBe("DRAFT");
});

// 5. 200 기존 DRAFT 응답 처리
it("returns the reused report on a 200 response, the same as a 201", async () => {
  setStoredToken(makeFakeJwt("DOCTOR"));
  vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));

  const report = await createClinicalReport(1, {
    report_type: "DOCTOR_REFERENCE",
    scope_type: "SINGLE_ENCOUNTER",
    encounter_ids: [1],
  });

  expect(report.id).toBe(1);
});

// 6. 올바른 GET URL
it("gets /reports/{report_id}", async () => {
  setStoredToken(makeFakeJwt("DOCTOR"));
  const fetchMock = mockFetchOnce(200, SAMPLE_REPORT);
  vi.stubGlobal("fetch", fetchMock);

  await getClinicalReport(1);

  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain("/reports/1");
  expect(options.method).toBe("GET");
});

// 7. 응답 타입과 백엔드 계약 일치 (핵심 필드가 그대로 전달되는지)
it("passes through every ClinicalReportOut field unchanged", async () => {
  setStoredToken(makeFakeJwt("DOCTOR"));
  vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));

  const report = await getClinicalReport(1);

  expect(report).toEqual(SAMPLE_REPORT);
});

// 8. JWT 또는 비밀번호 로그 미출력
it("never logs the token to the console", async () => {
  const token = makeFakeJwt("DOCTOR");
  setStoredToken(token);
  const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
  vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_REPORT));

  await getClinicalReport(1);

  for (const call of consoleSpy.mock.calls) {
    expect(call.map(String).join(" ")).not.toContain(token);
  }
  consoleSpy.mockRestore();
});
