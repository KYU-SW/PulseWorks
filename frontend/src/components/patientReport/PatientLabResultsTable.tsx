import { PatientLabResult } from "../../api/patientReports";
import { formatDateTime, STATUS_LABELS } from "../labTrend/LabTrendPresentation";
import TermOrPlainText from "./TermOrPlainText";

// LabResultsTableSection.tsx(의사용)를 수정하거나 재사용하지 않는다 —
// 이 표는 환자용 응답(PatientLabResult, 내부 id/rule_id/encounter_id/
// source_type 없음)만을 위한 독립된 컴포넌트다. formatDateTime과
// STATUS_LABELS(둘 다 순수 헬퍼)만 LabTrendPresentation.tsx에서
// 그대로 재사용한다.
export default function PatientLabResultsTable({ labResults }: { labResults: PatientLabResult[] }) {
  if (labResults.length === 0) return null;

  return (
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
        {labResults.map((lab, index) => (
          <tr key={`${lab.test_name}-${lab.measured_at}-${index}`}>
            <td>
              <TermOrPlainText text={lab.test_name} />
            </td>
            <td>
              {lab.value}
              {lab.unit}
            </td>
            <td>
              {lab.reference_low}-{lab.reference_high}
              {lab.unit}
            </td>
            <td>{formatDateTime(lab.measured_at)}</td>
            <td>{STATUS_LABELS[lab.status] ?? lab.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
