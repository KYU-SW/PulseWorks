import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import {
  approveClinicalReport,
  ClinicalReportOut,
  generateReportNarrative,
  getClinicalReport,
  patchClinicalReport,
  rejectClinicalReport,
} from "../api/clinicalReports";
import ReportRenderer from "../components/report/ReportRenderer";
import { formatDateTime } from "../components/labTrend/LabTrendPresentation";

type LoadState = "loading" | "success" | "forbidden" | "notFound" | "error";
type ConfirmStep = "idle" | "confirming";

const REPORT_STATUS_LABELS: Record<string, string> = {
  DRAFT: "초안",
  APPROVED: "승인",
  REJECTED: "반려",
};

const GENERIC_SAVE_ERROR = "보고서를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.";
const GENERIC_APPROVE_ERROR = "보고서를 승인하지 못했습니다. 잠시 후 다시 시도해 주세요.";
const GENERIC_REJECT_ERROR = "보고서를 반려하지 못했습니다. 잠시 후 다시 시도해 주세요.";

// 유효한 report_id 형식(양의 정수)이 아니면 API를 호출하지 않고 바로
// 404와 동일한 일반화된 안내를 보여준다.
function isValidReportId(reportId: string | undefined): boolean {
  return !!reportId && /^\d+$/.test(reportId);
}

// 공백만 있는 입력은 null로 보낸다 — 백엔드도 동일하게 정규화하지만,
// 프론트에서 먼저 정규화해 저장 후 화면에 남는 값이 항상 일관되게 한다.
function blankToNull(value: string): string | null {
  return value.trim() === "" ? null : value;
}

export default function ClinicalReportPreviewPage() {
  const { reportId } = useParams();
  const [report, setReport] = useState<ClinicalReportOut | null>(null);
  const [state, setState] = useState<LoadState>(
    isValidReportId(reportId) ? "loading" : "notFound"
  );
  const hasFetchedRef = useRef(false);

  const [isGeneratingNarrative, setIsGeneratingNarrative] = useState(false);
  const [narrativeError, setNarrativeError] = useState<string | null>(null);

  const [editableNarrative, setEditableNarrative] = useState("");
  const [editableHandoffNote, setEditableHandoffNote] = useState("");
  const [editablePatientGuidance, setEditablePatientGuidance] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [approveStep, setApproveStep] = useState<ConfirmStep>("idle");
  const [isApproving, setIsApproving] = useState(false);
  const [approveError, setApproveError] = useState<string | null>(null);

  const [rejectStep, setRejectStep] = useState<ConfirmStep>("idle");
  const [isRejecting, setIsRejecting] = useState(false);
  const [rejectError, setRejectError] = useState<string | null>(null);

  // report가 갱신될 때마다(최초 로딩, 생성, 저장, 승인, 반려 성공 후)
  // 편집 중인 textarea 값을 그 시점의 저장된 내용으로 맞춘다.
  useEffect(() => {
    if (!report) return;
    setEditableNarrative(report.content.narrative ?? "");
    setEditableHandoffNote(report.content.handoff_note ?? "");
    setEditablePatientGuidance(report.content.patient_guidance ?? "");
  }, [report]);

  async function loadReport() {
    if (!isValidReportId(reportId)) {
      setState("notFound");
      return;
    }
    setState("loading");
    try {
      const result = await getClinicalReport(reportId!);
      setReport(result);
      setState("success");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) return; // client.ts가 전역 로그아웃 처리
        if (err.status === 403) {
          setState("forbidden");
          return;
        }
        if (err.status === 404) {
          setState("notFound");
          return;
        }
      }
      setState("error");
    }
  }

  async function handleGenerateNarrative() {
    if (!report || isGeneratingNarrative) return; // 중복 요청 방지
    setNarrativeError(null);
    setIsGeneratingNarrative(true);
    try {
      const updated = await generateReportNarrative(report.id);
      // 반환된 ClinicalReport로 화면 상태만 갱신한다 — 전체 페이지 새로고침이나
      // 추가 EMR API 호출 없음.
      setReport(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return; // 전역 처리
      setNarrativeError("설명문을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
    } finally {
      setIsGeneratingNarrative(false);
    }
  }

  async function handleSave() {
    if (!report || isSaving) return; // 중복 요청 방지
    setSaveError(null);
    setIsSaving(true);
    try {
      const updated = await patchClinicalReport(report.id, {
        narrative: blankToNull(editableNarrative),
        handoff_note: blankToNull(editableHandoffNote),
        patient_guidance: blankToNull(editablePatientGuidance),
      });
      setReport(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setSaveError(GENERIC_SAVE_ERROR);
    } finally {
      setIsSaving(false);
    }
  }

  async function handleApproveConfirmed() {
    if (!report || isApproving) return; // 중복 요청 방지
    setApproveError(null);
    setIsApproving(true);
    try {
      const updated = await approveClinicalReport(report.id);
      setReport(updated);
      setApproveStep("idle");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      // 409는 "설명문을 먼저 작성/생성하세요" 같은 사용자가 바로 행동할 수
      // 있는 안전한 문구이므로 그대로 보여준다.
      if (err instanceof ApiError && err.status === 409) {
        setApproveError(err.message);
      } else {
        setApproveError(GENERIC_APPROVE_ERROR);
      }
      setApproveStep("idle");
    } finally {
      setIsApproving(false);
    }
  }

  async function handleRejectConfirmed() {
    if (!report || isRejecting) return; // 중복 요청 방지
    setRejectError(null);
    setIsRejecting(true);
    try {
      const updated = await rejectClinicalReport(report.id);
      setReport(updated);
      setRejectStep("idle");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setRejectError(GENERIC_REJECT_ERROR);
      setRejectStep("idle");
    } finally {
      setIsRejecting(false);
    }
  }

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;
    if (isValidReportId(reportId)) {
      loadReport();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

  const canGenerateNarrative =
    !!report && report.status === "DRAFT" && report.content.narrative === null;
  const isEditable = !!report && (report.status === "DRAFT" || report.status === "REJECTED");
  const anyActionInFlight = isSaving || isApproving || isRejecting;

  return (
    <div>
      <h1>진료참고 보고서</h1>

      {state === "loading" && <p>보고서를 불러오는 중...</p>}

      {state === "notFound" && (
        <p role="alert">보고서를 찾을 수 없거나 조회할 수 없습니다.</p>
      )}

      {state === "forbidden" && <p role="alert">보고서를 조회할 권한이 없습니다.</p>}

      {state === "error" && (
        <div>
          <p role="alert">보고서를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
          <button onClick={loadReport}>다시 시도</button>
        </div>
      )}

      {state === "success" && report && (
        <div>
          <p>
            상태: <strong>{REPORT_STATUS_LABELS[report.status] ?? report.status}</strong>
          </p>
          <p>보고서 생성일: {formatDateTime(report.created_at)}</p>
          <p>마지막 수정일: {formatDateTime(report.last_modified_at)}</p>
          <p>보고서 범위: 단일 진료 방문</p>
          <p>이 보고서의 모든 임상 데이터는 합성(가짜) 교육용 데이터입니다.</p>

          {report.status === "DRAFT" && (
            <p>이 보고서는 의료진 검토 전 초안이며 현재 환자에게 공개되지 않습니다.</p>
          )}
          {report.status === "REJECTED" && (
            <p>반려된 보고서입니다. 내용을 저장하면 다시 초안 상태가 됩니다.</p>
          )}
          {report.status === "APPROVED" && <p>승인된 보고서는 수정할 수 없습니다.</p>}

          {canGenerateNarrative && (
            <div>
              <button onClick={handleGenerateNarrative} disabled={isGeneratingNarrative}>
                {isGeneratingNarrative ? "설명문을 생성하는 중..." : "Mock 설명문 생성"}
              </button>
              {narrativeError && <p role="alert">{narrativeError}</p>}
            </div>
          )}

          {isEditable && (
            <section aria-labelledby="edit-section-heading">
              <h2 id="edit-section-heading">서술형 내용 편집</h2>
              <p>
                이 내용은 정해진 규칙으로 만든 결정적 Mock 초안이거나 의료진이 직접 작성한
                내용이며, 의료진의 검토가 필요합니다. 환자에게는 아직 공개되지 않습니다.
              </p>

              <div>
                <label htmlFor="narrative-textarea">설명문</label>
                <br />
                <textarea
                  id="narrative-textarea"
                  value={editableNarrative}
                  onChange={(e) => setEditableNarrative(e.target.value)}
                  disabled={anyActionInFlight}
                />
              </div>

              <div>
                <label htmlFor="handoff-note-textarea">인수인계 메모</label>
                <br />
                <textarea
                  id="handoff-note-textarea"
                  value={editableHandoffNote}
                  onChange={(e) => setEditableHandoffNote(e.target.value)}
                  disabled={anyActionInFlight}
                />
              </div>

              <div>
                <label htmlFor="patient-guidance-textarea">환자 안내문</label>
                <br />
                <textarea
                  id="patient-guidance-textarea"
                  value={editablePatientGuidance}
                  onChange={(e) => setEditablePatientGuidance(e.target.value)}
                  disabled={anyActionInFlight}
                />
              </div>

              <button onClick={handleSave} disabled={anyActionInFlight}>
                {isSaving ? "저장하는 중..." : "저장"}
              </button>
              {saveError && <p role="alert">{saveError}</p>}
            </section>
          )}

          {report.status === "APPROVED" && (
            <section aria-labelledby="approved-content-heading">
              <h2 id="approved-content-heading">서술형 내용 (읽기 전용)</h2>
              <p>설명문: {report.content.narrative ?? "(없음)"}</p>
              <p>인수인계 메모: {report.content.handoff_note ?? "(없음)"}</p>
              <p>환자 안내문: {report.content.patient_guidance ?? "(없음)"}</p>
            </section>
          )}

          {report.status === "DRAFT" && (
            <div>
              {approveStep === "idle" && (
                <button onClick={() => setApproveStep("confirming")} disabled={anyActionInFlight}>
                  승인
                </button>
              )}
              {approveStep === "confirming" && (
                <div role="group" aria-label="승인 확인">
                  <p>정말 승인하시겠습니까?</p>
                  <button onClick={handleApproveConfirmed} disabled={isApproving}>
                    {isApproving ? "승인하는 중..." : "승인 확정"}
                  </button>
                  <button onClick={() => setApproveStep("idle")} disabled={isApproving}>
                    취소
                  </button>
                </div>
              )}
              {approveError && <p role="alert">{approveError}</p>}

              {rejectStep === "idle" && (
                <button onClick={() => setRejectStep("confirming")} disabled={anyActionInFlight}>
                  반려
                </button>
              )}
              {rejectStep === "confirming" && (
                <div role="group" aria-label="반려 확인">
                  <p>정말 반려하시겠습니까?</p>
                  <button onClick={handleRejectConfirmed} disabled={isRejecting}>
                    {isRejecting ? "반려하는 중..." : "반려 확정"}
                  </button>
                  <button onClick={() => setRejectStep("idle")} disabled={isRejecting}>
                    취소
                  </button>
                </div>
              )}
              {rejectError && <p role="alert">{rejectError}</p>}
            </div>
          )}

          <ReportRenderer content={report.content} />

          <p>
            <Link to={`/doctor/patients/${report.patient_id}`}>환자 타임라인으로 돌아가기</Link>
          </p>
          <p>
            <Link to="/doctor">담당 환자 목록으로 돌아가기</Link>
          </p>
        </div>
      )}
    </div>
  );
}
