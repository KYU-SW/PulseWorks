import { formatDateTime, STATUS_LABELS } from "../../labTrend/LabTrendPresentation";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

// 검사 추세(그래프, lab_trends)와는 별개로 이 환자/Encounter의 모든
// LabResult 원본을 표로 나열한다 — 그룹화하지 않은 개별 검사명 표시.
export default function LabResultsTableSection({
  snapshot,
  title,
  emptyBehavior,
}: SectionComponentProps) {
  const hasData = snapshot.lab_results.length > 0;
  return (
    <SectionShell id="lab_results" title={title} hasData={hasData} emptyBehavior={emptyBehavior}>
      <table>
        <thead>
          <tr>
            <th scope="col">검사명</th>
            <th scope="col">값</th>
            <th scope="col">참고범위</th>
            <th scope="col">측정 시각</th>
            <th scope="col">판정</th>
          </tr>
        </thead>
        <tbody>
          {snapshot.lab_results.map((lab) => (
            <tr key={lab.id}>
              <td>{lab.test_name}</td>
              <td>
                {lab.value}
                {lab.unit}
              </td>
              <td>
                {lab.reference_low}-{lab.reference_high}
                {lab.unit}
              </td>
              <td>{formatDateTime(lab.measured_at)}</td>
              <td>{STATUS_LABELS[lab.status as keyof typeof STATUS_LABELS] ?? lab.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </SectionShell>
  );
}
