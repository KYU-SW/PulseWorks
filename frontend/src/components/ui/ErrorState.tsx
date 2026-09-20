interface ErrorStateProps {
  title: string;
  description?: React.ReactNode;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

export default function ErrorState({
  title,
  description,
  onRetry,
  retryLabel = "다시 시도",
  className,
}: ErrorStateProps) {
  return (
    <div role="alert" className={["ui-error-state", className].filter(Boolean).join(" ")}>
      <p>{title}</p>
      {description && <p>{description}</p>}
      {onRetry && (
        <button type="button" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}
