interface LoadingStateProps {
  label: string;
  className?: string;
}

// 오류가 아니므로 role="alert"를 붙이지 않는다. 불필요한 애니메이션도
// 넣지 않는다 — 텍스트만으로 로딩 상태를 알린다.
export default function LoadingState({ label, className }: LoadingStateProps) {
  return (
    <p className={["ui-loading-state", className].filter(Boolean).join(" ")} aria-live="polite">
      {label}
    </p>
  );
}
