import { Link, LinkProps } from "react-router-dom";
import { ButtonVariant } from "./Button";

interface LinkButtonProps extends LinkProps {
  variant?: ButtonVariant;
}

// 버튼처럼 보이되 실제로는 내비게이션이다 — react-router-dom의 Link를
// 그대로 쓰고 button 요소로 렌더링하지 않는다(링크와 버튼의 역할을
// 혼동하지 않는다는 원칙).
export default function LinkButton({ variant = "primary", className, children, ...rest }: LinkButtonProps) {
  const classNames = ["ui-link-button", `ui-button--${variant}`, className].filter(Boolean).join(" ");

  return (
    <Link className={classNames} {...rest}>
      {children}
    </Link>
  );
}
