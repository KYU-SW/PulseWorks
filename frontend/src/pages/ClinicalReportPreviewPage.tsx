import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { ClinicalReportOut, getClinicalReport } from "../api/clinicalReports";
import ReportRenderer from "../components/report/ReportRenderer";
import { formatDateTime } from "../components/labTrend/LabTrendPresentation";

type LoadState = "loading" | "success" | "forbidden" | "notFound" | "error";

const REPORT_STATUS_LABELS: Record<string, string> = {
  DRAFT: "초안",
  APPROVED: "승인",
  REJECTED: "반려",
};

// 유효한 report_id 형식(양의 정수)이 아니면 API를 호출하지 않고 바로
// 404와 동일한 일반화된 안내를 보여준다.
function isValidReportId(reportId: string | undefined): boolean {
  return !!reportId && /^\d+$/.test(reportId);
}

export default function ClinicalReportPreviewPage() {
  const { reportId } = useParams();
  const [report, setReport] = useState<ClinicalReportOut | null>(null);
  const [state, setState] = useState<LoadState>(
    isValidReportId(reportId) ? "loading" : "notFound"
  );
  const hasFetchedRef = useRef(false);

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

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;
    if (isValidReportId(reportId)) {
      loadReport();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

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
