import { useState } from "react";
import { formatDateTime } from "../../labTrend/LabTrendPresentation";
import StatusBadge from "../../ui/StatusBadge";
import { SectionComponentProps } from "../sectionProps";
import SectionShell from "../SectionShell";

// UX-1C: "참고범위 밖"은 status가 구조화된 Backend 값(SnapshotLabResult.
// status)으로 이미 HIGH/LOW인 경우만을 뜻한다 - NORMAL/UNKNOWN은 제외.
// Frontend는 이 두 값을 비교만 할 뿐 수치로 재계산하지 않는다.
const OUT_OF_RANGE_STATUSES = new Set(["HIGH", "LOW"]);

// 검사 추세(그래프, lab_trends)와는 별개로 이 환자/Encounter의 모든
// LabResult 원본을 표로 나열한다 — 그룹화하지 않은 개별 검사명 표시.
export default function LabResultsTableSection({
  snapshot,
  title,
  emptyBehavior,
}: SectionComponentProps) {
  const [showOutOfRangeOnly, setShowOutOfRangeOnly] = useState(false);
  const hasData = snapshot.lab_results.length > 0;
  // 원본 snapshot.lab_results는 건드리지 않고 파생 배열만 만든다.
  const visibleLabResults = showOutOfRangeOnly
    ? snapshot.lab_results.filter((lab) => OUT_OF_RANGE_STATUSES.has(lab.status))
    : snapshot.lab_results;

  return (
    <SectionShell id="lab_results" title={title} hasData={hasData} emptyBehavior={emptyBehavior}>
      {/* 필터를 표 바로 위의 section toolbar로 묶는다(동작은 그대로). */}
      <div className="lab-toolbar">
        <label className="toggle-chip">
          <input
            type="checkbox"
            checked={showOutOfRangeOnly}
            onChange={(e) => setShowOutOfRangeOnly(e.target.checked)}
          />{" "}
          참고범위 밖만 보기
        </label>
      </div>

      {visibleLabResults.length === 0 ? (
        <p className="page-note">참고범위를 벗어난 검사결과가 없습니다.</p>
      ) : (
        <div className="lab-table-frame">
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
            {visibleLabResults.map((lab) => (
              <tr key={lab.id}>
                <td className="cell-primary">{lab.test_name}</td>
                <td className="cell-numeric cell-primary">
                  {lab.value}
                  {lab.unit}
                </td>
                <td className="cell-numeric cell-muted">
                  {lab.reference_low}-{lab.reference_high}
                  {lab.unit}
                </td>
                <td className="cell-nowrap cell-muted">{formatDateTime(lab.measured_at)}</td>
                <td>
                  <StatusBadge kind="lab" status={lab.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}
    </SectionShell>
  );
}
