import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { getPatientReport, PatientClinicalReportDetail } from "../api/patientReports";
import { formatDateTime } from "../components/labTrend/LabTrendPresentation";
import PatientAllergiesList from "../components/patientReport/PatientAllergiesList";
import PatientLabResultsTable from "../components/patientReport/PatientLabResultsTable";
import PatientLabTrendGroupView from "../components/patientReport/PatientLabTrendGroupView";
import PatientPrescriptionsList from "../components/patientReport/PatientPrescriptionsList";

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
    <div>
      {state === "loading" && <p>보고서를 불러오는 중...</p>}

      {state === "forbidden" && <p role="alert">이 보고서를 조회할 권한이 없습니다.</p>}

      {state === "notFound" && <p role="alert">보고서를 찾을 수 없거나 조회할 수 없습니다.</p>}

      {state === "error" && (
        <div>
          <p role="alert">보고서를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
          <button onClick={load}>다시 시도</button>
        </div>
      )}

      {state === "success" && report && (
        <div>
          <h1>승인된 보고서</h1>
          <p>상태: 승인됨</p>
          <p>승인일: {formatDateTime(report.reviewed_at)}</p>
          <p>진료일: {formatDate(report.encounter_date)}</p>
          <p>
            진료과: {DEPARTMENT_LABELS[report.department] ?? report.department} / 진료 형태:{" "}
            {ENCOUNTER_TYPE_LABELS[report.encounter_type] ?? report.encounter_type}
          </p>

          {report.narrative && (
            <section>
              <h2>승인된 설명</h2>
              <p>{report.narrative}</p>
            </section>
          )}

          {report.patient_guidance && (
            <section>
              <h2>의료진 안내</h2>
              <p>{report.patient_guidance}</p>
            </section>
          )}

          {report.diagnoses.length > 0 && (
            <section>
              <h2>진단 기록</h2>
              <ul>
                {report.diagnoses.map((d, index) => (
                  <li key={`${d.diagnosed_at}-${index}`}>
                    {d.description} — {formatDateTime(d.diagnosed_at)}
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section>
            <h2>검사결과</h2>
            <PatientLabResultsTable labResults={report.lab_results} />
          </section>

          {report.lab_trends.length > 0 && (
            <section>
              <h2>검사 추세</h2>
              {report.lab_trends.map((group) => (
                <PatientLabTrendGroupView key={`${group.test_name}|${group.unit}`} group={group} />
              ))}
            </section>
          )}

          {report.prescriptions.length > 0 && (
            <section>
              <h2>처방 기록</h2>
              <PatientPrescriptionsList prescriptions={report.prescriptions} />
            </section>
          )}

          {report.allergies.length > 0 && (
            <section>
              <h2>알레르기</h2>
              <PatientAllergiesList allergies={report.allergies} />
            </section>
          )}

          {report.evidence.length > 0 && (
            <section>
              <h2>근거 자료</h2>
              <ul>
                {report.evidence.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            </section>
          )}

          <p style={{ whiteSpace: "pre-line" }}>{report.safety_notice}</p>
        </div>
      )}
    </div>
  );
}
