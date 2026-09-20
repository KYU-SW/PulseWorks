type AlertVariant = "error" | "warning" | "info" | "success";

interface AlertBoxProps {
  variant: AlertVariant;
  title?: React.ReactNode;
  children: React.ReactNode;
  // 호출부가 명시적으로 지정한다 — variant만 보고 role="alert"를 자동으로
  // 강제하지 않는다(정상 정보 안내까지 alert가 되는 것을 막기 위해).
  role?: "alert";
  className?: string;
}

export default function AlertBox({ variant, title, children, role, className }: AlertBoxProps) {
  return (
    <div role={role} className={["ui-alert", `ui-alert--${variant}`, className].filter(Boolean).join(" ")}>
      {title && <strong>{title}</strong>}
      <div>{children}</div>
    </div>
  );
}
