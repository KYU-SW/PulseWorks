interface FormFieldProps {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  description?: string;
  error?: string;
  required?: boolean;
  className?: string;
}

// 상태 없는 레이아웃 컴포넌트다 — 입력값이나 onChange를 관리하지 않고,
// children(input/textarea)을 새 요소로 교체하거나 cloneElement로
// 가로채지 않는다. description/error 요소는 안정적인 id(`${htmlFor}-
// description`/`${htmlFor}-error`)를 가지므로, 호출부가 자신의 입력
// 요소에 aria-describedby="{htmlFor}-description {htmlFor}-error"를
// 직접 붙일 수 있다.
export default function FormField({
  label,
  htmlFor,
  children,
  description,
  error,
  required,
  className,
}: FormFieldProps) {
  return (
    <div className={["ui-form-field", className].filter(Boolean).join(" ")}>
      <label className="ui-form-field__label" htmlFor={htmlFor}>
        {label}
        {required && " *"}
      </label>
      {children}
      {description && (
        <p id={`${htmlFor}-description`} className="ui-form-field__description">
          {description}
        </p>
      )}
      {error && (
        <p id={`${htmlFor}-error`} className="ui-form-field__error">
          {error}
        </p>
      )}
    </div>
  );
}
