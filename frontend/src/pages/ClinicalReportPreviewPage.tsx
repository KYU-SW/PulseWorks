import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
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
import AppShell from "../components/ui/AppShell";
import AppHeader from "../components/ui/AppHeader";
import Navigation from "../components/ui/Navigation";
import PageHeader from "../components/ui/PageHeader";
import Card from "../components/ui/Card";
import SectionCard from "../components/ui/SectionCard";
import StatusBadge from "../components/ui/StatusBadge";
import AlertBox from "../components/ui/AlertBox";
import FormField from "../components/ui/FormField";
import Button from "../components/ui/Button";
import LinkButton from "../components/ui/LinkButton";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";

type LoadState = "loading" | "success" | "forbidden" | "notFound" | "error";
type ConfirmStep = "idle" | "confirming";

const GENERIC_SAVE_ERROR = "보고서를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.";
const GENERIC_APPROVE_ERROR = "보고서를 승인하지 못했습니다. 잠시 후 다시 시도해 주세요.";
const GENERIC_REJECT_ERROR = "보고서를 반려하지 못했습니다. 잠시 후 다시 시도해 주세요.";
// generateReportNarrative()가 ApiError가 아닌 오류(예: 네트워크 자체
// 실패)로 거부될 때만 쓰는 최후 대체 문구 — 백엔드가 이미 안전한
// detail 메시지를 주는 일반적인 경우(503/502)에는 그 메시지를 그대로
// 쓴다(아래 handleGenerateNarrative).
const GENERIC_NARRATIVE_ERROR = "설명문을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.";
// Task D2: 프론트엔드 timeout 전용 안내 — 서버/Ollama 작업은 프론트
// abort로 취소되지 않으므로, 확정된 실패가 아니라 "계속 처리 중일 수
// 있다"는 사실을 정직하게 알리고 새로고침으로 확인하도록 안내한다.
const TIMEOUT_NARRATIVE_ERROR =
  "설명문 생성이 평소보다 오래 걸리고 있습니다. 서버에서는 계속 처리 중일 수 있으니, 잠시 후 보고서를 새로고침하여 완료 여부를 확인해 주세요.";
const NARRATIVE_TIMEOUT_MS = 75000;

// AbortController.abort()로 발생하는 오류는 브라우저에서는 DOMException,
// 테스트 환경에서는 평범한 Error일 수 있어 instanceof 체크에 의존하지
// 않고 name만으로 판별한다.
function isAbortError(err: unknown): boolean {
  return (
    typeof err === "object" &&
    err !== null &&
    (err as { name?: unknown }).name === "AbortError"
  );
}

// 유효한 report_id 형식(양의 정수)이 아니면 API를 호출하지 않고 바로
// 404와 동일한 일반화된 안내를 보여준다.
function isValidReportId(reportId: string | undefined): boolean {
  return !!reportId && /^\d+$/.test(reportId);
}

// Task D1: narrative_source/narrative_edited_by_clinician으로 정확한
// 출처 문구를 고른다. 예상하지 못한 값(및 null — Task D1 이전에 만들어진
// 기존 보고서)은 전부 "출처 불명" 문구로 안전하게 처리한다 — 실제
// vendor/모델 이름이나 과장된 품질 보증 표현은 어디에도 넣지 않는다.
function getNarrativeSourceNotice(
  source: string | null,
  edited: boolean
): { line1: string; line2: string } {
  if (source === "mock" && !edited) {
    return {
      line1: "결정적 Mock 기반 검토 전 초안",
      line2: "의료진 검토 전에는 환자에게 공개되지 않습니다.",
    };
  }
  if (source === "mock" && edited) {
    return {
      line1: "Mock 초안을 바탕으로 의료진이 수정한 내용",
      line2: "의료진 승인 전에는 환자에게 공개되지 않습니다.",
    };
  }
  if (source === "llm" && !edited) {
    return {
      line1: "AI로 생성된 검토 전 초안",
      line2: "의료진 검토 전에는 환자에게 공개되지 않습니다.",
    };
  }
  if (source === "llm" && edited) {
    return {
      line1: "AI 초안을 바탕으로 의료진이 수정한 내용",
      line2: "의료진 승인 전에는 환자에게 공개되지 않습니다.",
    };
  }
  if (source === "clinician") {
    return {
      line1: "의료진이 직접 작성한 검토 전 내용",
      line2: "승인 전에는 환자에게 공개되지 않습니다.",
    };
  }
  return {
    line1: "의료진 검토 전 초안",
    line2: "승인 전에는 환자에게 공개되지 않습니다.",
  };
}

// 공백만 있는 입력은 null로 보낸다 — 백엔드도 동일하게 정규화하지만,
// 프론트에서 먼저 정규화해 저장 후 화면에 남는 값이 항상 일관되게 한다.
function blankToNull(value: string): string | null {
  return value.trim() === "" ? null : value;
}

export default function ClinicalReportPreviewPage() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { role, logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const [report, setReport] = useState<ClinicalReportOut | null>(null);
  const [state, setState] = useState<LoadState>(
    isValidReportId(reportId) ? "loading" : "notFound"
  );
  const hasFetchedRef = useRef(false);

  const [isGeneratingNarrative, setIsGeneratingNarrative] = useState(false);
  const [narrativeError, setNarrativeError] = useState<string | null>(null);
  const [narrativeSucceeded, setNarrativeSucceeded] = useState(false);

  // Task D2: timeout/페이지 이동 취소/늦은 응답 무시를 위한 상태.
  // state가 아니라 ref로 두는 이유 — 렌더링과 무관하게 비동기 콜백
  // (setTimeout, fetch의 성공/실패 콜백)에서 "지금 활성 요청이 맞는지"를
  // 확인하는 용도이기 때문이다.
  const narrativeAbortControllerRef = useRef<AbortController | null>(null);
  const narrativeTimeoutIdRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const narrativeRequestIdRef = useRef(0);
  const narrativeTimedOutRequestIdRef = useRef<number | null>(null);
  const isMountedRef = useRef(true);

  const [editableNarrative, setEditableNarrative] = useState("");
  const [editableHandoffNote, setEditableHandoffNote] = useState("");
  const [editablePatientGuidance, setEditablePatientGuidance] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSucceeded, setSaveSucceeded] = useState(false);

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

    // 방어적 처리: 이미 활성 요청이 남아 있다면(정상적으로는 버튼이
    // disabled라 발생하지 않지만) 먼저 안전하게 정리한다.
    if (narrativeAbortControllerRef.current) {
      narrativeAbortControllerRef.current.abort();
    }
    if (narrativeTimeoutIdRef.current) {
      clearTimeout(narrativeTimeoutIdRef.current);
      narrativeTimeoutIdRef.current = null;
    }

    const requestId = ++narrativeRequestIdRef.current;
    const controller = new AbortController();
    narrativeAbortControllerRef.current = controller;

    setNarrativeError(null);
    setNarrativeSucceeded(false); // 새 생성 시작 전 이전 성공 안내를 지운다.
    setIsGeneratingNarrative(true);

    narrativeTimeoutIdRef.current = setTimeout(() => {
      // 이 요청이 이미 다른 요청으로 대체됐다면 아무것도 하지 않는다.
      if (narrativeRequestIdRef.current !== requestId) return;
      narrativeTimedOutRequestIdRef.current = requestId;
      controller.abort();
    }, NARRATIVE_TIMEOUT_MS);

    try {
      const updated = await generateReportNarrative(report.id, controller.signal);

      // 늦게 도착한 응답(이미 새 요청이 시작됐거나 언마운트됨)은 화면
      // 상태를 절대 덮어쓰지 않는다.
      if (!isMountedRef.current || narrativeRequestIdRef.current !== requestId) return;

      // 반환된 ClinicalReport로 화면 상태만 갱신한다 — 전체 페이지 새로고침이나
      // 추가 EMR API 호출 없음.
      setReport(updated);
      setNarrativeSucceeded(true);
    } catch (err) {
      if (!isMountedRef.current || narrativeRequestIdRef.current !== requestId) return;

      if (isAbortError(err)) {
        // timeout으로 인한 abort만 사용자에게 안내한다. 언마운트나(다른
        // 요청으로 대체되는 경우는 위에서 이미 걸러짐) 그 외의 abort는
        // 보여줄 화면이 없거나 보여줄 필요가 없으므로 아무 문구도
        // 표시하지 않는다.
        if (narrativeTimedOutRequestIdRef.current === requestId) {
          setNarrativeError(TIMEOUT_NARRATIVE_ERROR);
        }
        return;
      }

      if (err instanceof ApiError && err.status === 401) return; // 전역 처리
      if (err instanceof ApiError && err.status === 502) {
        // 검증 실패 — 백엔드의 안전한 문구에 "내용은 바뀌지 않았다"는
        // 안심 문장만 프론트에서 덧붙인다(백엔드는 그 문장을 주지 않음).
        setNarrativeError(`${err.message} 보고서 내용은 변경되지 않았습니다.`);
      } else if (err instanceof ApiError && err.status === 503) {
        // 서비스 사용 불가 — 백엔드가 이미 안전하게 일반화한 detail
        // 메시지를 그대로 쓴다(승인 409 처리와 같은 패턴).
        setNarrativeError(err.message);
      } else {
        // 502/503 외의 상태(500, 예상치 못한 오류 등)는 백엔드 detail을
        // 신뢰하지 않는다 — 그 두 상태만 "안전하다고 약속된" 문구다.
        setNarrativeError(GENERIC_NARRATIVE_ERROR);
      }
    } finally {
      if (narrativeRequestIdRef.current === requestId) {
        if (narrativeTimeoutIdRef.current) {
          clearTimeout(narrativeTimeoutIdRef.current);
          narrativeTimeoutIdRef.current = null;
        }
        if (narrativeAbortControllerRef.current === controller) {
          narrativeAbortControllerRef.current = null;
        }
        if (isMountedRef.current) {
          setIsGeneratingNarrative(false);
        }
      }
    }
  }

  async function handleSave() {
    if (!report || isSaving) return; // 중복 요청 방지
    setSaveError(null);
    setSaveSucceeded(false); // 새 저장 시작 전 이전 성공 안내를 지운다.
    // 생성 성공 안내와 저장 성공 안내가 동시에 뜨지 않도록, 저장을
    // 시작하면 이전 생성 성공 안내도 함께 지운다 — 가장 최근 동작의
    // 결과만 보여준다.
    setNarrativeSucceeded(false);
    setIsSaving(true);
    try {
      const updated = await patchClinicalReport(report.id, {
        narrative: blankToNull(editableNarrative),
        handoff_note: blankToNull(editableHandoffNote),
        patient_guidance: blankToNull(editablePatientGuidance),
      });
      setReport(updated);
      setSaveSucceeded(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) return;
      setSaveError(GENERIC_SAVE_ERROR);
    } finally {
      setIsSaving(false);
    }
  }

  // 세 필드 중 하나라도 다시 수정하면 이전 저장·생성 성공 안내를 지운다.
  function handleEditableFieldChange(setField: (value: string) => void, value: string) {
    setField(value);
    setSaveSucceeded(false);
    setNarrativeSucceeded(false);
  }

  async function handleApproveConfirmed() {
    if (!report || isApproving) return; // 중복 요청 방지
    setApproveError(null);
    setIsApproving(true);
    try {
      const updated = await approveClinicalReport(report.id);
      setReport(updated);
      setApproveStep("idle");
      setSaveSucceeded(false); // APPROVED가 되면 저장 편집 영역 자체가 사라지므로 상태도 정리한다.
      setNarrativeSucceeded(false);
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

  // Task D2: 페이지 이동 등으로 컴포넌트가 사라지면 진행 중인 설명문
  // 생성 요청을 취소하고, 이후 그 요청의 결과가 와도 이미 사라진
  // 컴포넌트의 상태를 바꾸지 않도록 한다.
  useEffect(() => {
    // StrictMode(개발 모드)는 이 effect를 mount→cleanup→mount 순으로 한 번
    // 더 실행한다 — 그 첫 번째 cleanup이 아래에서 isMountedRef.current를
    // false로 만들므로, 여기서 다시 true로 되돌리지 않으면 "진짜" mount
    // 이후에도 영구히 false로 남아 생성 성공/실패 응답이 전부 무시된다.
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (narrativeAbortControllerRef.current) {
        narrativeAbortControllerRef.current.abort();
      }
      if (narrativeTimeoutIdRef.current) {
        clearTimeout(narrativeTimeoutIdRef.current);
        narrativeTimeoutIdRef.current = null;
      }
    };
  }, []);

  const canGenerateNarrative =
    !!report && report.status === "DRAFT" && report.content.narrative === null;
  const isEditable = !!report && (report.status === "DRAFT" || report.status === "REJECTED");
  const anyActionInFlight = isSaving || isApproving || isRejecting;

  return (
    <AppShell
      header={
        <AppHeader brand="EMR 프로토타입">
          <Navigation role={role!} onLogout={handleLogout} />
        </AppHeader>
      }
    >
      <PageHeader title="진료참고 보고서" />

      {state === "loading" && <LoadingState label="보고서를 불러오는 중..." />}

      {state === "notFound" && (
        <AlertBox variant="error" role="alert">
          보고서를 찾을 수 없거나 조회할 수 없습니다.
        </AlertBox>
      )}

      {state === "forbidden" && (
        <AlertBox variant="error" role="alert">
          보고서를 조회할 권한이 없습니다.
        </AlertBox>
      )}

      {state === "error" && (
        <ErrorState
          title="보고서를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
          onRetry={loadReport}
        />
      )}

      {state === "success" && report && (
        <div className="page-stack">
          <Card>
            <p>
              상태: <StatusBadge kind="report" status={report.status} />
            </p>
            <p>보고서 생성일: {formatDateTime(report.created_at)}</p>
            <p>마지막 수정일: {formatDateTime(report.last_modified_at)}</p>
            <p>보고서 범위: 단일 진료 방문</p>
            <p>이 보고서의 모든 임상 데이터는 합성(가짜) 교육용 데이터입니다.</p>

            {report.status === "DRAFT" && (
              <AlertBox variant="info">
                이 보고서는 의료진 검토 전 초안이며 현재 환자에게 공개되지 않습니다.
              </AlertBox>
            )}
            {report.status === "REJECTED" && (
              <AlertBox variant="warning">
                반려된 보고서입니다. 내용을 저장하면 다시 초안 상태가 됩니다.
              </AlertBox>
            )}
            {report.status === "APPROVED" && (
              <AlertBox variant="success">승인된 보고서는 수정할 수 없습니다.</AlertBox>
            )}
          </Card>

          {canGenerateNarrative && (
            <Card>
              <Button
                variant="primary"
                onClick={handleGenerateNarrative}
                disabled={isGeneratingNarrative}
                loading={isGeneratingNarrative}
              >
                {isGeneratingNarrative ? "설명문 초안 생성 중..." : "설명문 초안 생성"}
              </Button>
              {narrativeError && (
                <AlertBox variant="error" role="alert">
                  {narrativeError}
                </AlertBox>
              )}
            </Card>
          )}

          {/* canGenerateNarrative와 별개로 둔다 — 생성이 성공하면 report의
              narrative가 채워져 canGenerateNarrative가 바로 false가
              되어 위 Card 전체가 사라지므로, 성공 안내를 그 Card 안에
              두면 뜨자마자 같은 렌더링에서 사라져 버린다. */}
          {narrativeSucceeded && report.status === "DRAFT" && (
            <div className="report-save-feedback" aria-live="polite">
              <p className="report-save-feedback__success" role="status">
                설명문 초안이 생성되었습니다. 내용을 검토한 뒤 저장하거나 승인하세요.
              </p>
            </div>
          )}

          {isEditable && (
            <SectionCard title="서술형 내용 편집">
              {(() => {
                const notice = getNarrativeSourceNotice(
                  report.content.narrative_source,
                  report.content.narrative_edited_by_clinician
                );
                return (
                  <>
                    <p>{notice.line1}</p>
                    <p>{notice.line2}</p>
                  </>
                );
              })()}

              <FormField label="설명문" htmlFor="narrative-textarea">
                <textarea
                  id="narrative-textarea"
                  value={editableNarrative}
                  onChange={(e) => handleEditableFieldChange(setEditableNarrative, e.target.value)}
                  disabled={anyActionInFlight}
                />
              </FormField>

              <FormField label="인수인계 메모" htmlFor="handoff-note-textarea">
                <textarea
                  id="handoff-note-textarea"
                  value={editableHandoffNote}
                  onChange={(e) => handleEditableFieldChange(setEditableHandoffNote, e.target.value)}
                  disabled={anyActionInFlight}
                />
              </FormField>

              <FormField label="환자 안내문" htmlFor="patient-guidance-textarea">
                <textarea
                  id="patient-guidance-textarea"
                  value={editablePatientGuidance}
                  onChange={(e) => handleEditableFieldChange(setEditablePatientGuidance, e.target.value)}
                  disabled={anyActionInFlight}
                />
              </FormField>

              <div className="report-save-actions">
                <Button
                  type="button"
                  variant="primary"
                  onClick={handleSave}
                  disabled={anyActionInFlight}
                  loading={isSaving}
                >
                  {isSaving ? "저장하는 중..." : "저장"}
                </Button>
                <div className="report-save-feedback" aria-live="polite">
                  {saveSucceeded && (
                    <p className="report-save-feedback__success" role="status">
                      저장되었습니다.
                    </p>
                  )}
                </div>
              </div>
              {saveError && (
                <AlertBox variant="error" role="alert">
                  {saveError}
                </AlertBox>
              )}
            </SectionCard>
          )}

          {report.status === "APPROVED" && (
            <SectionCard title="서술형 내용 (읽기 전용)">
              <p>설명문: {report.content.narrative ?? "(없음)"}</p>
              <p>인수인계 메모: {report.content.handoff_note ?? "(없음)"}</p>
              <p>환자 안내문: {report.content.patient_guidance ?? "(없음)"}</p>
            </SectionCard>
          )}

          {report.status === "DRAFT" && (
            <Card>
              {approveStep === "idle" && (
                <Button
                  variant="primary"
                  onClick={() => setApproveStep("confirming")}
                  disabled={anyActionInFlight}
                >
                  승인
                </Button>
              )}
              {approveStep === "confirming" && (
                <div role="group" aria-label="승인 확인">
                  <p>정말 승인하시겠습니까?</p>
                  <Button
                    variant="primary"
                    onClick={handleApproveConfirmed}
                    disabled={isApproving}
                    loading={isApproving}
                  >
                    {isApproving ? "승인하는 중..." : "승인 확정"}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setApproveStep("idle")}
                    disabled={isApproving}
                  >
                    취소
                  </Button>
                </div>
              )}
              {approveError && (
                <AlertBox variant="error" role="alert">
                  {approveError}
                </AlertBox>
              )}

              {rejectStep === "idle" && (
                <Button
                  variant="danger"
                  onClick={() => setRejectStep("confirming")}
                  disabled={anyActionInFlight}
                >
                  반려
                </Button>
              )}
              {rejectStep === "confirming" && (
                <div role="group" aria-label="반려 확인">
                  <p>정말 반려하시겠습니까?</p>
                  <Button
                    variant="danger"
                    onClick={handleRejectConfirmed}
                    disabled={isRejecting}
                    loading={isRejecting}
                  >
                    {isRejecting ? "반려하는 중..." : "반려 확정"}
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => setRejectStep("idle")}
                    disabled={isRejecting}
                  >
                    취소
                  </Button>
                </div>
              )}
              {rejectError && (
                <AlertBox variant="error" role="alert">
                  {rejectError}
                </AlertBox>
              )}
            </Card>
          )}

          <Card>
            <ReportRenderer content={report.content} />
          </Card>

          <p>
            <LinkButton to={`/doctor/patients/${report.patient_id}`} variant="ghost">
              환자 타임라인으로 돌아가기
            </LinkButton>
          </p>
          <p>
            <LinkButton to="/doctor" variant="ghost">
              담당 환자 목록으로 돌아가기
            </LinkButton>
          </p>
        </div>
      )}
    </AppShell>
  );
}
