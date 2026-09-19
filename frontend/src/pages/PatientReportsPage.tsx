import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { getPatientReports, PatientReportListItem } from "../api/patientReports";
import { formatDateTime } from "../components/labTrend/LabTrendPresentation";

// encounter_date는 시각 없는 순수 날짜 문자열("YYYY-MM-DD")이라, 시각까지
// 표시하는 formatDateTime 대신 날짜만 보여주는 별도 헬퍼를 쓴다. new
// Date(isoDate)로 파싱하면 시간대에 따라 하루가 밀릴 수 있어, 문자열을
// 직접 나눠 조립한다(백엔드 evidence 문구와 같은 "YYYY년 M월 D일" 형식).
function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${year}년 ${Number(month)}월 ${Number(day)}일`;
}

type LoadState = "loading" | "success" | "forbidden" | "error";

const DEPARTMENT_LABELS: Record<string, string> = {
  ENDOCRINOLOGY: "내분비내과",
  ORTHOPEDICS: "정형외과",
  EMERGENCY_MEDICINE: "응급의학과",
};

// 환자에게 이해 가능한 보고서 유형 라벨. 백엔드는 report_type을 필터
// 기준으로 쓰지 않고 그대로 내려줄 뿐이라, 화면에 보여줄 한국어 표현은
// 프론트엔드에서만 담당한다.
const REPORT_TYPE_LABELS: Record<string, string> = {
  DOCTOR_REFERENCE: "진료 보고서",
  HANDOFF: "인수인계 보고서",
  PATIENT_EASY: "환자용 쉬운 보고서",
};

export default function PatientReportsPage() {
  const [state, setState] = useState<LoadState>("loading");
  const [reports, setReports] = useState<PatientReportListItem[]>([]);

  async function load() {
    setState("loading");
    try {
      const result = await getPatientReports();
      setReports(result);
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
  }, []);

  return (
    <div>
      <h1>승인된 보고서</h1>
      <p>담당 의료진이 승인한 보고서만 여기에 표시됩니다.</p>

      {state === "loading" && <p>보고서 목록을 불러오는 중...</p>}

      {state === "forbidden" && <p role="alert">보고서 목록을 조회할 권한이 없습니다.</p>}

      {state === "error" && (
        <div>
          <p role="alert">보고서 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
          <button onClick={load}>다시 시도</button>
        </div>
      )}

      {state === "success" && reports.length === 0 && (
        <p>현재 확인할 수 있는 승인 보고서가 없습니다.</p>
      )}

      {state === "success" && reports.length > 0 && (
        <ul>
          {reports.map((report) => (
            <li key={report.id}>
              <Link to={`/patient/reports/${report.id}`}>
                {formatDate(report.encounter_date)}{" "}
                {DEPARTMENT_LABELS[report.department] ?? report.department}{" "}
                {REPORT_TYPE_LABELS[report.report_type] ?? report.report_type} (승인일:{" "}
                {formatDateTime(report.reviewed_at)})
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
