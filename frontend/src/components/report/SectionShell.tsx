import { ReactNode } from "react";
import { ReportSectionEmptyBehavior } from "../../reportTemplates/types";

/**
 * 모든 보고서 섹션이 공유하는 뼈대 — heading/aria-labelledby 연결과
 * hide vs show_empty_state 분기를 한 곳에서만 구현한다. 데이터가 없는
 * 정상 상태이므로 role="alert"는 쓰지 않는다(그건 Task 15의 실제 API
 * 오류 상태에서만 쓴다).
 */
export default function SectionShell({
  id,
  title,
  hasData,
  emptyBehavior,
  emptyText,
  children,
}: {
  id: string;
  title: string;
  hasData: boolean;
  emptyBehavior: ReportSectionEmptyBehavior;
  emptyText?: string;
  children: ReactNode;
}) {
  if (!hasData && emptyBehavior === "hide") {
    return null;
  }

  const headingId = `${id}-heading`;

  return (
    <section aria-labelledby={headingId} className={`report-section report-section--${id}`}>
      <h2 id={headingId}>{title}</h2>
      {hasData ? children : <p>{emptyText}</p>}
    </section>
  );
}
