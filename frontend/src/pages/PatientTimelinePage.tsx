import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { createClinicalReport } from "../api/clinicalReports";
import {
  getPatientTimeline,
  PatientTimeline,
  TimelineEventType,
} from "../api/timeline";
import {
  formatVitalSignValue,
  VitalType as VitalSignType,
} from "../components/vitalSign/formatVitalSign";
import LabTrendSection from "../components/LabTrendSection";
import EncounterSummaryCard, {
  groupTimelineByEncounter,
} from "../components/encounterSummary/EncounterSummaryCard";
import AppShell from "../components/ui/AppShell";
import AppHeader from "../components/ui/AppHeader";
import Navigation from "../components/ui/Navigation";
import PageHeader from "../components/ui/PageHeader";
import Card from "../components/ui/Card";
import SectionCard from "../components/ui/SectionCard";
import Button from "../components/ui/Button";
import AlertBox from "../components/ui/AlertBox";
import EmptyState from "../components/ui/EmptyState";
import LoadingState from "../components/ui/LoadingState";
import ErrorState from "../components/ui/ErrorState";
import LinkButton from "../components/ui/LinkButton";

type LoadState = "loading" | "success" | "forbidden" | "notFound" | "error";

const EVENT_TYPE_LABELS: Record<TimelineEventType, string> = {
  ENCOUNTER: "방문",
  DIAGNOSIS: "진단",
  LAB_RESULT: "검사결과",
  PRESCRIPTION: "처방",
  CLINICAL_NOTE: "진료기록",
  VITAL_SIGN: "활력징후", // Task F4-A
};

const SOURCE_TYPE_LABELS: Record<string, string> = {
  PATIENT_REPORTED: "환자 입력",
  INSTITUTION_GENERATED: "의료기관 생성",
};

export default function PatientTimelinePage() {
  const { patientId } = useParams();
  const navigate = useNavigate();
  const { role, logout } = useAuth();

  function handleLogout() {
    logout();
    navigate("/login");
  }

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
    <AppShell
      header={
        <AppHeader brand="EMR 프로토타입">
          <Navigation role={role!} onLogout={handleLogout} />
        </AppHeader>
      }
    >
      <p className="page-back-link">
        <LinkButton to="/doctor" variant="ghost">
          ← 담당 환자 목록으로 돌아가기
        </LinkButton>
      </p>

      {state === "loading" && <LoadingState label="환자 타임라인을 불러오는 중..." />}

      {state === "notFound" && (
        <AlertBox variant="error" role="alert">
          환자를 찾을 수 없습니다.
        </AlertBox>
      )}

      {state === "forbidden" && (
        <AlertBox variant="error" role="alert">
          이 환자의 타임라인을 조회할 권한이 없습니다.
        </AlertBox>
      )}

      {state === "error" && (
        <ErrorState
          title="타임라인을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
          onRetry={loadTimeline}
        />
      )}

      {state === "success" && data && (
        <div className="page-stack">
          <Card className="patient-header">
            <PageHeader
              title={data.patient.name}
              description={`MRN: ${data.patient.mrn} · 생년월일: ${data.patient.birth_date}`}
            />
            <p className="page-note">이 화면의 모든 임상 데이터는 합성(가짜) 교육용 데이터입니다.</p>
          </Card>

          {patientId && <LabTrendSection patientId={patientId} />}

          {reportError && (
            <AlertBox variant="error" role="alert">
              {reportError}
            </AlertBox>
          )}

          <SectionCard title="Encounter 요약">
            {(() => {
              const encounterSummaries = groupTimelineByEncounter(data.timeline);
              return encounterSummaries.length === 0 ? (
                <EmptyState title="표시할 Encounter 요약이 없습니다." />
              ) : (
                <ul className="encounter-summary-list">
                  {encounterSummaries.map((summary) => (
                    <li key={summary.encounterItem.encounter_id}>
                      <EncounterSummaryCard summary={summary} />
                    </li>
                  ))}
                </ul>
              );
            })()}
          </SectionCard>

          <SectionCard title="임상 타임라인">
            {data.timeline.length === 0 ? (
              <EmptyState title="표시할 타임라인 항목이 없습니다." />
            ) : (
              // 시각/이벤트 종류/제목/세부값/진료과·출처를 열 단위로 정돈한 목록.
              // 표시하는 값은 기존과 같고, 출처가 없을 때의 "-" 자리표시만 생략한다.
              <ul className="timeline-list">
                {data.timeline.map((item) => {
                  const isCreating = creatingEncounterIds.has(item.encounter_id);
                  return (
                    <li key={`${item.event_type}-${item.id}`} className="timeline-item">
                      <time className="timeline-item__time" dateTime={item.event_time}>
                        {new Date(item.event_time).toLocaleString()}
                      </time>
                      <div className="timeline-item__body">
                        <div className="timeline-item__head">
                          <strong className="timeline-item__type">{EVENT_TYPE_LABELS[item.event_type]}</strong>
                          <span className="timeline-item__title">{item.title}</span>
                        </div>
                        <div className="timeline-item__detail">
                          <span>
                            {item.event_type === "VITAL_SIGN" &&
                            item.vital_type &&
                            item.value &&
                            item.unit
                              ? formatVitalSignValue(
                                  item.vital_type as VitalSignType,
                                  item.value,
                                  item.value_secondary ?? null,
                                  item.unit
                                )
                              : item.summary}
                          </span>
                          {item.event_type === "ENCOUNTER" && item.bmi && (
                            <span>{" · "}BMI {item.bmi}</span>
                          )}
                        </div>
                        <div className="timeline-item__meta">
                          <span>{item.department}</span>
                          {item.source_type && (
                            <span>{SOURCE_TYPE_LABELS[item.source_type] ?? item.source_type}</span>
                          )}
                        </div>
                        {item.event_type === "VITAL_SIGN" &&
                          item.quality_warnings &&
                          item.quality_warnings.length > 0 && (
                            <AlertBox variant="warning">
                              {item.quality_warnings.join(" ")}
                            </AlertBox>
                          )}
                      </div>
                      {item.event_type === "ENCOUNTER" && (
                        <div className="timeline-item__action">
                          <Button
                            variant="secondary"
                            onClick={() => handleCreateReport(item.encounter_id)}
                            disabled={isCreating}
                          >
                            {isCreating ? "보고서를 생성하는 중..." : "이 방문으로 진료참고 보고서 생성"}
                          </Button>
                        </div>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </SectionCard>
        </div>
      )}
    </AppShell>
  );
}
