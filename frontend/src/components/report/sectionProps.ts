import { EmrSnapshot } from "../../api/clinicalReports";
import { ReportSectionEmptyBehavior } from "../../reportTemplates/types";

// 모든 보고서 섹션 컴포넌트가 받는 공통 props. title/emptyBehavior는
// departmentReportTemplates.ts(단일 원본)에서 내려오며, 섹션 컴포넌트가
// 자체적으로 다시 정의하지 않는다 — 그러면 설정이 두 곳에 흩어진다.
export type SectionComponentProps = {
  snapshot: EmrSnapshot;
  title: string;
  emptyBehavior: ReportSectionEmptyBehavior;
};
