import { formatDateTime } from "../../labTrend/LabTrendPresentation";
import { formatVitalSignValue, VitalType } from "../../vitalSign/formatVitalSign";
import StatusBadge from "../../ui/StatusBadge";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

// Task F4-B의 app/routers/encounters.py와 동일한 값 - 이 프로젝트의
// 기존 패턴대로 각 파일이 독립적으로 라벨을 선언한다(VitalSignsSection.
// tsx와 동일).
const VITAL_TYPE_LABELS: Record<string, string> = {
  BLOOD_PRESSURE: "혈압",
  BODY_HEIGHT: "키",
  BODY_WEIGHT: "체중",
  BODY_TEMPERATURE: "체온",
  HEART_RATE: "맥박",
  RESPIRATORY_RATE: "호흡수",
  PULSE_OXIMETRY: "산소포화도",
};

// UX-1D: 보고서 근거(Evidence)의 유일한 source는 이미 동결된
// ReportContentSnapshot.emr_snapshot의 구조화 데이터(vital_signs/
// lab_results/diagnoses)다. source_record_ids 원문 문자열은 과거 내부
// 식별자 노출 UI(SourceRecordIdsSection)가 쓰던 값인데, 이 컴포넌트는
// 그 필드를 전혀 읽지 않는다 - AI가 자체적으로 주장하는 evidence_tags/
// mentioned_measurements/Narrative 문장도 쓰지 않는다. 추가 fetch도
// 하지 않는다(현재 DB 상태가 아니라 보고서 생성/승인 시점에 동결된 이
// snapshot만 사용). 문장 단위 citation(어떤 문장이 어떤 근거를
// 인용했는지)은 현재 데이터 모델로 지원되지 않으므로 만들지 않는다 -
// "이 보고서 생성 시 동결된 임상 근거 데이터 전체"만 보여준다.
export default function EvidenceSection({ snapshot, title, emptyBehavior }: SectionComponentProps) {
  const hasVitalSigns = snapshot.vital_signs.length > 0;
  const hasLabResults = snapshot.lab_results.length > 0;
  const hasDiagnoses = snapshot.diagnoses.length > 0;
  // 내부 source_record_ids가 있다는 사실만으로 근거가 있다고 표시하지
  // 않는다 - 실제 구조화 데이터 존재 여부만 본다.
  const hasData = hasVitalSigns || hasLabResults || hasDiagnoses;

  return (
    <SectionShell id="source_record_ids" title={title} hasData={hasData} emptyBehavior={emptyBehavior}>
      <div className="evidence-groups">
      {hasVitalSigns && (
        <div className="evidence-group">
          <h3>활력징후</h3>
          <ul>
            {snapshot.vital_signs.map((vital) => (
              <li key={vital.id}>
                {VITAL_TYPE_LABELS[vital.vital_type] ?? vital.vital_type}:{" "}
                {formatVitalSignValue(
                  vital.vital_type as VitalType,
                  vital.value,
                  vital.value_secondary,
                  vital.unit
                )}{" "}
                ({formatDateTime(vital.measured_at)})
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasLabResults && (
        <div className="evidence-group">
          <h3>검사결과</h3>
          <ul>
            {snapshot.lab_results.map((lab) => (
              <li key={lab.id}>
                {lab.test_name}: {lab.value}
                {lab.unit} (참고범위 {lab.reference_low}-{lab.reference_high}
                {lab.unit}) <StatusBadge kind="lab" status={lab.status} /> (
                {formatDateTime(lab.measured_at)})
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasDiagnoses && (
        <div className="evidence-group">
          <h3>진단</h3>
          <ul>
            {snapshot.diagnoses.map((diagnosis) => (
              <li key={diagnosis.id}>
                {diagnosis.description} (진단 코드: {diagnosis.code}) — {formatDateTime(diagnosis.diagnosed_at)}
              </li>
            ))}
          </ul>
        </div>
      )}
      </div>
    </SectionShell>
  );
}
