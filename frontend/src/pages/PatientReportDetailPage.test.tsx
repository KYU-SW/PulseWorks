import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setStoredToken } from "../api/client";
import { makeFakeJwt } from "../test/fakeJwt";
import PatientReportDetailPage from "./PatientReportDetailPage";

const SAMPLE_DETAIL = {
  id: 1,
  department: "ENDOCRINOLOGY",
  encounter_type: "OUTPATIENT",
  encounter_date: "2026-03-10",
  reviewed_at: "2026-03-11T00:00:00Z",
  narrative: "의사가 승인한 설명문입니다.",
  patient_guidance: "물을 충분히 드세요.",
  diagnoses: [{ description: "2형 당뇨병 신규 진단 (합성 데이터)", diagnosed_at: "2026-03-10T09:00:00Z" }],
  lab_results: [
    {
      test_name: "HbA1c", value: 7.2, unit: "%", reference_low: 4.0, reference_high: 6.0,
      measured_at: "2026-03-10T09:00:00Z", status: "HIGH",
    },
    {
      test_name: "알 수 없는 검사", value: 1, unit: "unit", reference_low: 0, reference_high: 2,
      measured_at: "2026-03-10T09:00:00Z", status: "NORMAL",
    },
  ],
  lab_trends: [
    {
      test_name: "HbA1c",
      unit: "%",
      points: [
        { value: 7.2, unit: "%", reference_low: 4.0, reference_high: 6.0, measured_at: "2026-03-10T09:00:00Z", status: "HIGH" },
        { value: 7.8, unit: "%", reference_low: 4.0, reference_high: 6.0, measured_at: "2026-06-10T09:00:00Z", status: "HIGH" },
      ],
    },
  ],
  prescriptions: [{ medication_name: "Metformin", dosage: "500mg", prescribed_at: "2026-03-10T09:00:00Z" }],
  allergies: [{ substance: "Penicillin", reaction: "두드러기", severity: "MODERATE" }],
  evidence: ["2026년 3월 10일 내분비내과 HbA1c 검사"],
  safety_notice:
    "검사결과와 참고범위만으로 건강상태를 판단하지 마세요.\n자세한 의미는 담당 의료진에게 확인하세요.",
};

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    text: async () => JSON.stringify(body),
  });
}

function renderAt(reportId: string) {
  return render(
    <MemoryRouter initialEntries={[`/patient/reports/${reportId}`]}>
      <Routes>
        <Route path="/patient/reports/:reportId" element={<PatientReportDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("PatientReportDetailPage", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    sessionStorage.clear();
  });

  it("shows a loading state before the report resolves", () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    expect(screen.getByText("보고서를 불러오는 중...")).toBeInTheDocument();
  });

  it("shows a forbidden message on 403", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(403, { detail: "Forbidden" }));
    renderAt("1");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("이 보고서를 조회할 권한이 없습니다.");
  });

  it("shows the generalized not-found message on 404", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(404, { detail: "보고서를 찾을 수 없거나 조회할 수 없습니다." }));
    renderAt("999999");

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("보고서를 찾을 수 없거나 조회할 수 없습니다.");
  });

  it("treats a non-numeric report id as not-found without calling the API", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    const fetchMock = mockFetchOnce(200, SAMPLE_DETAIL);
    vi.stubGlobal("fetch", fetchMock);
    renderAt("not-a-number");

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "보고서를 찾을 수 없거나 조회할 수 없습니다."
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows a generic error with a working retry button on a server error", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 500, json: async () => ({ detail: "boom" }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => SAMPLE_DETAIL });
    vi.stubGlobal("fetch", fetchMock);
    renderAt("1");
    const user = userEvent.setup();

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).not.toContain("boom");
    await user.click(screen.getByRole("button", { name: "다시 시도" }));

    await waitFor(() => expect(screen.getByText("승인된 보고서")).toBeInTheDocument());
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("shows the approved narrative and patient guidance", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    expect(await screen.findByText("의사가 승인한 설명문입니다.")).toBeInTheDocument();
    expect(screen.getByText("물을 충분히 드세요.")).toBeInTheDocument();
  });

  it("hides the patient guidance section when patient_guidance is null", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, { ...SAMPLE_DETAIL, patient_guidance: null }));
    renderAt("1");

    await screen.findByText("의사가 승인한 설명문입니다.");
    expect(screen.queryByText("의료진 안내")).not.toBeInTheDocument();
  });

  it("never renders handoff_note, ClinicalNote, or SafetyAlert content anywhere", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    const { container } = renderAt("1");

    await screen.findByText("의사가 승인한 설명문입니다.");
    const text = container.textContent ?? "";
    expect(text).not.toContain("handoff");
    expect(text).not.toContain("인수인계");
    expect(text).not.toContain("안전 알림");
    expect(text).not.toContain("진료기록 미리보기");
  });

  it("never renders a raw internal id or source_record_ids string", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    const { container } = renderAt("1");

    await screen.findByText("의사가 승인한 설명문입니다.");
    expect(container.textContent ?? "").not.toMatch(/lab_result:|encounter:|diagnosis:|prescription:/);
  });

  it("shows lab results and lab trends", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    await screen.findByText("의사가 승인한 설명문입니다.");
    const table = screen.getByRole("table");
    expect(within(table).getByText("7.2%")).toBeInTheDocument();
    expect(await screen.findByRole("img", { name: /검사값 추세 그래프/ })).toBeInTheDocument();
  });

  it("shows the Korean status label, not the raw HIGH/LOW/NORMAL value", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    await screen.findByText("의사가 승인한 설명문입니다.");
    expect(screen.getAllByText("높음").length).toBeGreaterThan(0);
    expect(screen.getAllByText("정상").length).toBeGreaterThan(0);
  });

  it("shows a MedicalTermButton for a registered test name and plain text for an unregistered one", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    const termButtons = await screen.findAllByRole("button", { name: /HbA1c/ });
    expect(termButtons.length).toBeGreaterThan(0);
    expect(screen.getByText("알 수 없는 검사")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /알 수 없는 검사/ })).not.toBeInTheDocument();
  });

  it("opens the medical term dialog when a registered term button is clicked", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");
    const user = userEvent.setup();

    const [termButton] = await screen.findAllByRole("button", { name: /HbA1c/ });
    await user.click(termButton);

    expect(screen.getByRole("dialog", { hidden: true })).toBeInTheDocument();
    expect(
      screen.getByText("지난 2~3개월 동안의 평균 혈당 수준을 보여주는 검사입니다.")
    ).toBeInTheDocument();
  });

  it("shows the encounter type (외래) as plain text, not a MedicalTermButton", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    await screen.findByText("의사가 승인한 설명문입니다.");
    expect(screen.getByText(/외래/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /외래/ })).not.toBeInTheDocument();
  });

  it("shows the patient-facing evidence phrase", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    expect(await screen.findByText("2026년 3월 10일 내분비내과 HbA1c 검사")).toBeInTheDocument();
  });

  it("always shows the common safety notice", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    expect(
      await screen.findByText((_, el) => el?.textContent === SAMPLE_DETAIL.safety_notice)
    ).toBeInTheDocument();
  });

  it("never renders an edit, approve, or reject button", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    await screen.findByText("의사가 승인한 설명문입니다.");
    expect(screen.queryByRole("button", { name: /저장/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /승인/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /반려/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("shows Metformin as a MedicationButton with the formatted dosage", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    expect(await screen.findByRole("button", { name: /메트포르민\(Metformin\)/ })).toBeInTheDocument();
    expect(screen.getByText(/500 mg/)).toBeInTheDocument();
  });

  it("opens the medication dialog and shows its plain-language definition", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: /메트포르민\(Metformin\)/ }));

    expect(
      screen.getByText("혈당 조절을 위해 사용될 수 있는 약물입니다.")
    ).toBeInTheDocument();
  });

  it("shows the allergy severity as a Korean label (MODERATE -> 중간)", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    renderAt("1");

    expect(await screen.findByText(/중간/)).toBeInTheDocument();
    expect(screen.queryByText("MODERATE")).not.toBeInTheDocument();
  });

  it("never renders raw SafetyAlert-style directives (stop taking / dangerous / discontinue)", async () => {
    setStoredToken(makeFakeJwt("PATIENT"));
    vi.stubGlobal("fetch", mockFetchOnce(200, SAMPLE_DETAIL));
    const { container } = renderAt("1");

    await screen.findByText("의사가 승인한 설명문입니다.");
    const text = container.textContent ?? "";
    expect(text).not.toContain("복용하지 마세요");
    expect(text).not.toContain("위험합니다");
    expect(text).not.toContain("중단하세요");
  });
});
