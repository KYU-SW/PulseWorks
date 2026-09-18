import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { createClinicalReport } from "../api/clinicalReports";
import {
  getPatientTimeline,
  PatientTimeline,
  TimelineEventType,
} from "../api/timeline";
import LabTrendSection from "../components/LabTrendSection";

type LoadState = "loading" | "success" | "forbidden" | "notFound" | "error";

const EVENT_TYPE_LABELS: Record<TimelineEventType, string> = {
  ENCOUNTER: "방문",
  DIAGNOSIS: "진단",
  LAB_RESULT: "검사결과",
  PRESCRIPTION: "처방",
  CLINICAL_NOTE: "진료기록",
};

const SOURCE_TYPE_LABELS: Record<string, string> = {
  PATIENT_REPORTED: "환자 입력",
  INSTITUTION_GENERATED: "의료기관 생성",
};

export default function PatientTimelinePage() {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<PatientTimeline | null>(null);
  const [state, setState] = useState<LoadState>("loading");
  const hasFetchedRef = useRef(false);
  // Encounter별로 독립적인 진행 상태를 추적한다 — 한 Encounter의 요청이
  // 진행 중이어도 다른 Encounter의 버튼은 막지 않는다.
  const [creatingEncounterIds, setCreatingEncounterIds] = useState<Set<number>>(new Set());
  const [reportError, setReportError] = useState<string | null>(null);

  async function handleCreateReport(encounterId: number) {
    if (!patientId || creatingEncounterIds.has(encounterId)) return; // 중복 클릭 방지
    setReportError(null);
    setCreatingEncounterIds((prev) => new Set(prev).add(encounterId));

    try {
      const report = await createClinicalReport(patientId, {
        report_type: "DOCTOR_REFERENCE",
        scope_type: "SINGLE_ENCOUNTER",
        encounter_ids: [encounterId],
      });
      // 201(신규 생성)과 200(기존 DRAFT 재사용) 모두 동일하게 성공 처리하고
      // 같은 미리보기 페이지로 이동한다 — 오류 상태를 남기지 않는다.
      navigate(`/doctor/reports/${report.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) return; // client.ts가 전역 로그아웃 처리
        if (err.status === 403) {
          setReportError("보고서를 생성할 권한이 없습니다.");
        } else if (err.status === 404) {
          setReportError("환자 또는 보고서 범위를 찾을 수 없거나 조회할 수 없습니다.");
        } else if (err.status === 422) {
          setReportError("선택한 방문으로 보고서를 생성할 수 없습니다.");
        } else {
          setReportError("보고서를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
        }
      } else {
        setReportError("보고서를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.");
      }
      setCreatingEncounterIds((prev) => {
        const next = new Set(prev);
        next.delete(encounterId);
        return next; // 실패 시에만 버튼을 다시 활성화한다 — 성공 시엔 페이지 이동
      });
    }
  }

  async function loadTimeline() {
    if (!patientId) return;
    setState("loading");
    try {
      const result = await getPatientTimeline(patientId);
      setData(result);
      setState("success");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          // client.ts가 세션을 정리하고 auth:unauthorized를 쏘아
          // ProtectedRoute가 /login으로 보낸다.
          return;
        }
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
    loadTimeline();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  return (
    <div>
      <p>
        <Link to="/doctor">← 담당 환자 목록으로 돌아가기</Link>
      </p>

      {state === "loading" && <p>환자 타임라인을 불러오는 중...</p>}

      {state === "notFound" && <p role="alert">환자를 찾을 수 없습니다.</p>}

      {state === "forbidden" && (
        <p role="alert">이 환자의 타임라인을 조회할 권한이 없습니다.</p>
      )}

      {state === "error" && (
        <div>
          <p role="alert">타임라인을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
          <button onClick={loadTimeline}>다시 시도</button>
        </div>
      )}

      {state === "success" && data && (
        <div>
          <h1>{data.patient.name}</h1>
          <p>MRN: {data.patient.mrn}</p>
          <p>생년월일: {data.patient.birth_date}</p>
          <p>이 화면의 모든 임상 데이터는 합성(가짜) 교육용 데이터입니다.</p>

          {patientId && <LabTrendSection patientId={patientId} />}

          {reportError && <p role="alert">{reportError}</p>}

          {data.timeline.length === 0 && <p>표시할 타임라인 항목이 없습니다.</p>}

          {data.timeline.length > 0 && (
            <ul>
              {data.timeline.map((item) => {
                const isCreating = creatingEncounterIds.has(item.encounter_id);
                return (
                  <li key={`${item.event_type}-${item.id}`}>
                    <span>{new Date(item.event_time).toLocaleString()}</span>{" — "}
                    <strong>{EVENT_TYPE_LABELS[item.event_type]}</strong>{" — "}
                    <span>{item.title}</span>{" — "}
                    <span>{item.summary}</span>{" — "}
                    <span>{item.department}</span>{" — "}
                    <span>
                      {item.source_type
                        ? SOURCE_TYPE_LABELS[item.source_type] ?? item.source_type
                        : "-"}
                    </span>
                    {item.event_type === "ENCOUNTER" && (
                      <>
                        {" — "}
                        <button
                          onClick={() => handleCreateReport(item.encounter_id)}
                          disabled={isCreating}
                        >
                          {isCreating ? "보고서를 생성하는 중..." : "이 방문으로 진료참고 보고서 생성"}
                        </button>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
