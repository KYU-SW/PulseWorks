interface EmptyStateProps {
  title: string;
  description?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

// 정상적인 빈 상태를 표현한다 — 오류가 아니므로 role="alert"를 붙이지
// 않는다.
export default function EmptyState({ title, description, action, className }: EmptyStateProps) {
  return (
    <div className={["ui-empty-state", className].filter(Boolean).join(" ")}>
      <p>{title}</p>
      {description && <p>{description}</p>}
      {action}
    </div>
  );
}
