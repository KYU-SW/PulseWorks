interface DataTableProps {
  children: React.ReactNode;
  className?: string;
  label?: string;
}

// 자료구조 기반 표 생성기가 아니다 — 기존 <table> 구조를 그대로 감싸는
// 반응형(overflow-x: auto) 래퍼일 뿐이다. 래퍼에 role="table"을 추가로
// 얹지 않는다(그러면 내부 table과 의미가 중복/충돌한다). label이 있으면
// role="region"으로 스크롤 영역에 접근 가능한 이름을 준다 — 이건
// "table role"이 아니라 영역(region) role이라 금지 대상이 아니다.
export default function DataTable({ children, className, label }: DataTableProps) {
  return (
    <div
      className={["ui-table-scroll", className].filter(Boolean).join(" ")}
      role={label ? "region" : undefined}
      aria-label={label}
    >
      {children}
    </div>
  );
}
