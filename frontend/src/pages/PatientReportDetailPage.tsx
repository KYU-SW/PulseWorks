import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { getPatientReport, PatientClinicalReportDetail } from "../api/patientReports";
import { formatDateTime } from "../components/labTrend/LabTrendPresentation";
import PatientAllergiesList from "../components/patientReport/PatientAllergiesList";
import PatientLabResultsTable from "../components/patientReport/PatientLabResultsTable";
import PatientLabTrendGroupView from "../components/patientReport/PatientLabTrendGroupView";
import PatientPrescriptionsList from "../components/patientReport/PatientPrescriptionsList";
import PatientVitalSignsList from "../components/patientReport/PatientVitalSignsList";
import AppShell from "../components/ui/AppShell";
import AppHeader from "../components/ui/AppHeader";
import Navigation from "../components/ui/Navigation";
import PageHeader from "../components/ui/PageHeader";
import Card from "../components/ui/Card";
import SectionCard from "../components/ui/SectionCard";
import StatusBadge from "../components/ui/StatusBadge";
import AlertBox from "../components/ui/AlertBox";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";

type LoadState = "loading" | "success" | "forbidden" | "notFound" | "error";

const DEPARTMENT_LABELS: Record<string, string> = {
  ENDOCRINOLOGY: "내분비내과",
  ORTHOPEDICS: "정형외과",
  EMERGENCY_MEDICINE: "응급의학과",
};

const ENCOUNTER_TYPE_LABELS: Record<string, string> = {
  OUTPATIENT: "외래",
  INPATIENT: "입원",
  EMERGENCY: "응급",
};

function isValidReportId(reportId: string | undefined): boolean {
  return !!reportId && /^\d+$/.test(reportId);
}

// encounter_date는 시각 없는 순수 날짜 문자열이라 formatDateTime 대신
// PatientReportsPage와 같은 방식으로 직접 조립한다.
function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${year}년 ${Number(month)}월 ${Number(day)}일`;
}

export default function PatientReportDetailPage() {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { role, logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const [report, setReport] = useState<PatientClinicalReportDetail | null>(null);
  const [state, setState] = useState<LoadState>(
    isValidReportId(reportId) ? "loading" : "notFound"
  );

  async function load() {
    if (!isValidReportId(reportId)) {
      setState("notFound");
      return;
    }
    setState("loading");
    try {
      const result = await getPatientReport(reportId!);
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
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportId]);

  return (
    <AppShell
      header={
        <AppHeader brand="EMR 프로토타입">
          <Navigation role={role!} onLogout={handleLogout} />
        </AppHeader>
      }
    >
      {state === "loading" && <LoadingState label="보고서를 불러오는 중..." />}

      {state === "forbidden" && (
        <AlertBox variant="error" role="alert">
          이 보고서를 조회할 권한이 없습니다.
        </AlertBox>
      )}

      {state === "notFound" && (
        <AlertBox variant="error" role="alert">
          보고서를 찾을 수 없거나 조회할 수 없습니다.
        </AlertBox>
      )}

      {state === "error" && (
        <ErrorState
          title="보고서를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
          onRetry={load}
        />
      )}

      {state === "success" && report && (
        <div className="page-stack">
          <PageHeader title="승인된 보고서" />

          <Card className="report-meta">
            <p>
              상태: <StatusBadge kind="report" status="APPROVED" />
            </p>
            <p>승인일: {formatDateTime(report.reviewed_at)}</p>
            <p>진료일: {formatDate(report.encounter_date)}</p>
            <p>
              진료과: {DEPARTMENT_LABELS[report.department] ?? report.department} / 진료 형태:{" "}
              {ENCOUNTER_TYPE_LABELS[report.encounter_type] ?? report.encounter_type}
            </p>
          </Card>

          {report.narrative && (
            <SectionCard title="승인된 설명" className="narrative-readonly">
              <p>{report.narrative}</p>
            </SectionCard>
          )}

          {report.patient_guidance && (
            <SectionCard title="의료진 안내" className="narrative-readonly">
              <p>{report.patient_guidance}</p>
            </SectionCard>
          )}

          {report.diagnoses.length > 0 && (
            <SectionCard title="진단 기록">
              <ul>
                {report.diagnoses.map((d, index) => (
                  <li key={`${d.diagnosed_at}-${index}`}>
                    {d.description} — {formatDateTime(d.diagnosed_at)}
                  </li>
                ))}
              </ul>
            </SectionCard>
          )}

          <SectionCard title="검사결과">
            <PatientLabResultsTable labResults={report.lab_results} />
          </SectionCard>

          {report.lab_trends.length > 0 && (
            <SectionCard title="검사 추세">
              {report.lab_trends.map((group) => (
                <PatientLabTrendGroupView key={`${group.test_name}|${group.unit}`} group={group} />
              ))}
            </SectionCard>
          )}

          {report.prescriptions.length > 0 && (
            <SectionCard title="처방 기록">
              <PatientPrescriptionsList prescriptions={report.prescriptions} />
            </SectionCard>
          )}

          {report.allergies.length > 0 && (
            <SectionCard title="알레르기">
              <PatientAllergiesList allergies={report.allergies} />
            </SectionCard>
          )}

          {report.vital_signs.length > 0 && (
            <SectionCard title="활력징후">
              <PatientVitalSignsList vitalSigns={report.vital_signs} />
            </SectionCard>
          )}

          {report.evidence.length > 0 && (
            <SectionCard title="근거 자료">
              <ul>
                {report.evidence.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </SectionCard>
          )}

          <AlertBox variant="info">
            <p style={{ whiteSpace: "pre-line" }}>{report.safety_notice}</p>
          </AlertBox>
        </div>
      )}
    </AppShell>
  );
}
