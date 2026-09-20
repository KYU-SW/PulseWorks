type StatusBadgeKind = "report" | "lab";

// Task 17(ClinicalReportPreviewPage)과 Task 11/18(LabTrendPresentation)에서
// 이미 검증된 라벨을 그대로 재사용한다 — 새 어휘를 만들지 않는다.
const REPORT_STATUS_LABELS: Record<string, string> = {
  DRAFT: "초안",
  APPROVED: "승인됨",
  REJECTED: "반려됨",
};

const LAB_STATUS_LABELS: Record<string, string> = {
  LOW: "낮음",
  NORMAL: "정상",
  HIGH: "높음",
  UNKNOWN: "판정불가",
};

const UNKNOWN_STATUS_FALLBACK = "알 수 없음";

interface StatusBadgeProps {
  kind: StatusBadgeKind;
  status: string;
  className?: string;
}

export default function StatusBadge({ kind, status, className }: StatusBadgeProps) {
  const labels = kind === "report" ? REPORT_STATUS_LABELS : LAB_STATUS_LABELS;
  const knownLabel = labels[status];
  const label = knownLabel ?? UNKNOWN_STATUS_FALLBACK;
  const modifier = knownLabel ? status.toLowerCase() : "unknown";

  return (
    <span
      className={["ui-status-badge", `ui-status-badge--${kind}-${modifier}`, className]
        .filter(Boolean)
        .join(" ")}
    >
      <span className="ui-status-badge__dot" aria-hidden="true" />
      {label}
    </span>
  );
}
