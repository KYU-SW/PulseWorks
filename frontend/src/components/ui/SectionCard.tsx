import { useId } from "react";

type HeadingLevel = 2 | 3 | 4;

interface SectionCardProps {
  title?: string;
  headingLevel?: HeadingLevel;
  children: React.ReactNode;
  className?: string;
}

// Task 14의 SectionShell(보고서 섹션 표시/숨김 전용)과 책임이 다르다 —
// 이 컴포넌트는 카드 표면 + 제목 연결만 담당하는 범용 레이아웃 조각이고,
// ReportRenderer/SectionShell은 이번 Task에서 수정하지 않는다.
export default function SectionCard({
  title,
  headingLevel = 2,
  children,
  className,
}: SectionCardProps) {
  const headingId = useId();
  const HeadingTag = `h${headingLevel}` as "h2" | "h3" | "h4";

  return (
    <section
      className={["ui-card", "ui-section-card", className].filter(Boolean).join(" ")}
      aria-labelledby={title ? headingId : undefined}
    >
      {title && (
        <HeadingTag id={headingId} className="ui-section-card__title">
          {title}
        </HeadingTag>
      )}
      {children}
    </section>
  );
}
