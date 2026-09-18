import { formatDateTime } from "../../labTrend/LabTrendPresentation";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

const PRIORITY_LABELS: Record<string, string> = {
  HIGH: "높음",
  MEDIUM: "중간",
  LOW: "낮음",
};

function explanationText(evidence: Record<string, unknown>): string | null {
  return typeof evidence.explanation === "string" ? evidence.explanation : null;
}

// Task 10에서 저장된 SafetyAlert를 그대로 표시한다 — 여기서 새로
// 판정하거나 대체 약물을 추천하지 않는다.
export default function SafetyAlertsSection({
  snapshot,
  title,
  emptyBehavior,
}: SectionComponentProps) {
  const hasData = snapshot.safety_alerts.length > 0;
  return (
    <SectionShell
      id="safety_alerts"
      title={title}
      hasData={hasData}
      emptyBehavior={emptyBehavior}
      emptyText="표시할 안전 알림이 없습니다."
    >
      <ul>
        {snapshot.safety_alerts.map((alert) => (
          <li key={alert.id}>
            <p>
              {alert.rule_id} — 우선순위:{" "}
              <strong>{PRIORITY_LABELS[alert.priority] ?? alert.priority}</strong>
            </p>
            {explanationText(alert.evidence) && <p>{explanationText(alert.evidence)}</p>}
            <p>생성 시각: {formatDateTime(alert.created_at)}</p>
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}
