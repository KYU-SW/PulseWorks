import { afterEach, expect, it, vi } from "vitest";
import { setStoredToken } from "./client";
import { makeFakeJwt } from "../test/fakeJwt";
import {
  approveClinicalReport,
  createClinicalReport,
  generateReportNarrative,
  getClinicalReport,
  patchClinicalReport,
  rejectClinicalReport,
} from "./clinicalReports";

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

// generateReportNarrative(): 올바른 POST URL, Bearer 토큰 재사용, 200 응답 반환
it("posts to /reports/{report_id}/generate-narrative and returns the updated report", async () => {
  setStoredToken(makeFakeJwt("DOCTOR"));
  const withNarrative = {
    ...SAMPLE_REPORT,
    content: { ...SAMPLE_REPORT.content, narrative: "생성된 설명문" },
  };
  const fetchMock = mockFetchOnce(200, withNarrative);
  vi.stubGlobal("fetch", fetchMock);

  const report = await generateReportNarrative(1);

  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain("/reports/1/generate-narrative");
  expect(options.method).toBe("POST");
  expect(report.content.narrative).toBe("생성된 설명문");
});

// patchClinicalReport(): 올바른 PATCH URL/메서드/본문
it("sends a PATCH with exactly the given fields", async () => {
  setStoredToken(makeFakeJwt("DOCTOR"));
  const patched = {
    ...SAMPLE_REPORT,
    content: { ...SAMPLE_REPORT.content, narrative: "수정된 설명" },
  };
  const fetchMock = mockFetchOnce(200, patched);
  vi.stubGlobal("fetch", fetchMock);

  const report = await patchClinicalReport(1, {
    narrative: "수정된 설명",
    handoff_note: null,
    patient_guidance: null,
  });

  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain("/reports/1");
  expect(options.method).toBe("PATCH");
  expect(JSON.parse(options.body)).toEqual({
    narrative: "수정된 설명",
    handoff_note: null,
    patient_guidance: null,
  });
  expect(report.content.narrative).toBe("수정된 설명");
});

// approveClinicalReport(): 올바른 POST URL
it("posts to /reports/{report_id}/approve", async () => {
  setStoredToken(makeFakeJwt("DOCTOR"));
  const approved = { ...SAMPLE_REPORT, status: "APPROVED" };
  const fetchMock = mockFetchOnce(200, approved);
  vi.stubGlobal("fetch", fetchMock);

  const report = await approveClinicalReport(1);

  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain("/reports/1/approve");
  expect(options.method).toBe("POST");
  expect(report.status).toBe("APPROVED");
});

// rejectClinicalReport(): 올바른 POST URL
it("posts to /reports/{report_id}/reject", async () => {
  setStoredToken(makeFakeJwt("DOCTOR"));
  const rejected = { ...SAMPLE_REPORT, status: "REJECTED" };
  const fetchMock = mockFetchOnce(200, rejected);
  vi.stubGlobal("fetch", fetchMock);

  const report = await rejectClinicalReport(1);

  const [url, options] = fetchMock.mock.calls[0];
  expect(String(url)).toContain("/reports/1/reject");
  expect(options.method).toBe("POST");
  expect(report.status).toBe("REJECTED");
});
