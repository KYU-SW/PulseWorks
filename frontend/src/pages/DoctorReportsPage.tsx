import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import {
  ClinicalReportListItem,
  ClinicalReportListResponse,
  listClinicalReports,
} from "../api/clinicalReports";
import { formatDateTime } from "../components/labTrend/LabTrendPresentation";
import AppShell from "../components/ui/AppShell";
import AppHeader from "../components/ui/AppHeader";
import Navigation from "../components/ui/Navigation";
import PageHeader from "../components/ui/PageHeader";
import FormField from "../components/ui/FormField";
import Button from "../components/ui/Button";
import DataTable from "../components/ui/DataTable";
import StatusBadge from "../components/ui/StatusBadge";
import LinkButton from "../components/ui/LinkButton";
import LoadingState from "../components/ui/LoadingState";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import AlertBox from "../components/ui/AlertBox";
import Card from "../components/ui/Card";

type LoadState = "loading" | "success" | "forbidden" | "error";

type StatusFilter = "" | "DRAFT" | "APPROVED" | "REJECTED";

// 환자용 PatientReportsPage.tsx와 독립적으로 동일한 라벨을 선언한다 —
// 이 프로젝트의 기존 관례(각 파일이 자신의 한글 라벨을 직접 선언)와
// 같다.
const REPORT_TYPE_LABELS: Record<string, string> = {
  DOCTOR_REFERENCE: "진료 보고서",
  HANDOFF: "인수인계 보고서",
  PATIENT_EASY: "환자용 쉬운 보고서",
};

const PAGE_SIZE = 20;

export default function DoctorReportsPage() {
  const { role, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [page, setPage] = useState(1);

  const [state, setState] = useState<LoadState>("loading");
  const [data, setData] = useState<ClinicalReportListResponse | null>(null);

  const hasActiveFilter = statusFilter !== "" || fromDate !== "" || toDate !== "";

  async function load() {
    setState("loading");
    try {
      const result = await listClinicalReports({
        status: statusFilter || undefined,
        from_date: fromDate || undefined,
        to_date: toDate || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setData(result);
      setState("success");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) return; // client.ts가 전역 로그아웃 처리
        if (err.status === 403) {
          setState("forbidden");
          return;
        }
      }
      setState("error");
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, fromDate, toDate, page]);

  function resetFilters() {
    setStatusFilter("");
    setFromDate("");
    setToDate("");
    setPage(1);
  }

  const hasNextPage = data ? data.page * data.page_size < data.total : false;
  const hasPrevPage = data ? data.page > 1 : false;

  return (
    <AppShell
      header={
        <AppHeader brand="EMR 프로토타입">
          <Navigation role={role!} onLogout={handleLogout} />
        </AppHeader>
      }
    >
      <PageHeader title="진료 보고서" description="담당 환자의 진료참고 보고서 목록입니다." />

      {/* 상태·기간 필터와 초기화를 하나의 toolbar로 묶는다(동작은 그대로). */}
      <Card className="filter-toolbar">
        <FormField label="상태" htmlFor="report-status-filter">
          <select
            id="report-status-filter"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value as StatusFilter);
              setPage(1);
            }}
          >
            <option value="">전체</option>
            <option value="DRAFT">초안</option>
            <option value="APPROVED">승인됨</option>
            <option value="REJECTED">반려됨</option>
          </select>
        </FormField>

        <FormField label="시작일" htmlFor="report-from-date">
          <input
            id="report-from-date"
            type="date"
            value={fromDate}
            onChange={(e) => {
              setFromDate(e.target.value);
              setPage(1);
            }}
          />
        </FormField>

        <FormField label="종료일" htmlFor="report-to-date">
          <input
            id="report-to-date"
            type="date"
            value={toDate}
            onChange={(e) => {
              setToDate(e.target.value);
              setPage(1);
            }}
          />
        </FormField>

        <div className="filter-toolbar__actions">
          <Button variant="secondary" onClick={resetFilters}>
            필터 초기화
          </Button>
        </div>
      </Card>

      {state === "loading" && <LoadingState label="진료 보고서 목록을 불러오는 중..." />}

      {state === "forbidden" && (
        <AlertBox variant="error" role="alert">
          진료 보고서 목록을 조회할 권한이 없습니다.
        </AlertBox>
      )}

      {state === "error" && (
        <ErrorState
          title="진료 보고서 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
          onRetry={load}
        />
      )}

      {state === "success" && data && data.items.length === 0 && (
        <EmptyState
          title={
            hasActiveFilter
              ? "조건에 맞는 진료 보고서가 없습니다."
              : "조회할 진료 보고서가 없습니다."
          }
        />
      )}

      {state === "success" && data && data.items.length > 0 && (
        <Card className="table-card">
          <DataTable label="진료 보고서 목록">
            <table>
              <thead>
                <tr>
                  <th scope="col">환자</th>
                  <th scope="col">Encounter</th>
                  <th scope="col">보고서 유형</th>
                  <th scope="col">상태</th>
                  <th scope="col">생성일</th>
                  <th scope="col">승인일</th>
                  <th scope="col" className="cell-action">액션</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item: ClinicalReportListItem) => (
                  <tr key={item.id}>
                    <td className="cell-primary">{`${item.patient_name} (${item.patient_mrn})`}</td>
                    <td className="cell-muted cell-numeric">
                      {item.encounter_id !== null ? `#${item.encounter_id}` : "-"}
                    </td>
                    <td>{REPORT_TYPE_LABELS[item.report_type] ?? item.report_type}</td>
                    <td>
                      <StatusBadge kind="report" status={item.status} />
                    </td>
                    <td className="cell-nowrap">{formatDateTime(item.created_at)}</td>
                    <td className="cell-nowrap cell-muted">
                      {item.reviewed_at ? formatDateTime(item.reviewed_at) : "-"}
                    </td>
                    <td className="cell-action">
                      <LinkButton to={`/doctor/reports/${item.id}`} variant="ghost">
                        보기
                      </LinkButton>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </DataTable>

          {/* 표 footer 형태의 페이지 이동(이전/다음 동작은 그대로). */}
          <nav className="pagination" aria-label="페이지 이동">
            <Button
              variant="secondary"
              onClick={() => setPage((p) => p - 1)}
              disabled={!hasPrevPage}
            >
              이전
            </Button>
            <span className="pagination__status">페이지 {data.page}</span>
            <Button
              variant="secondary"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNextPage}
            >
              다음
            </Button>
          </nav>
        </Card>
      )}
    </AppShell>
  );
}
