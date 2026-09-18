import { LabTrendPointsView } from "../../labTrend/LabTrendPresentation";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

// 저장된 스냅샷의 lab_trends를 그대로 그린다 — 추가 fetch를 하지 않는다.
// 그룹마다 이미 Task 9 판정(status/rule_id)이 포함되어 있어 여기서
// 새로 판정하지 않는다.
export default function LabTrendsSection({ snapshot, title, emptyBehavior }: SectionComponentProps) {
  const hasData = snapshot.lab_trends.length > 0;
  return (
    <SectionShell id="lab_trends" title={title} hasData={hasData} emptyBehavior={emptyBehavior}>
      {snapshot.lab_trends.map((group) => (
        <div key={`${group.test_name}|${group.unit}`}>
          <h3>
            {group.test_name} ({group.unit})
          </h3>
          <LabTrendPointsView points={group.points} unit={group.unit} testName={group.test_name} />
        </div>
      ))}
    </SectionShell>
  );
}
