import {
  LabTrendPresentationPoint,
  SingleResultCard,
  TrendChart,
} from "../labTrend/LabTrendPresentation";
import { PatientLabTrendGroup, PatientLabTrendPoint } from "../../api/patientReports";
import TermOrPlainText from "./TermOrPlainText";
import Card from "../ui/Card";

// TrendChart/SingleResultCard(LabTrendPresentation.tsx)는 타입 선언에
// rule_id/encounter_id/source_type을 요구하지만, 그 파일을 직접 확인한
// 결과 렌더링에서는 이 세 필드를 전혀 읽지 않는다. 환자용 API는 내부
// 정보 최소 노출을 위해 이 세 필드를 애초에 내려주지 않으므로, 의미
// 없는 값을 채워 넣는 대신 이 경계에서만 타입을 맞춰 준다 — 실제
// 객체에는 이 필드들이 존재하지 않는다. LabTrendPresentation.tsx
// 자체는 수정하지 않는다.
function toPresentationPoint(point: PatientLabTrendPoint): LabTrendPresentationPoint {
  return point as unknown as LabTrendPresentationPoint;
}

// TrendTable(같은 파일의 또 다른 export)은 재사용하지 않는다 — "자료
// 출처"(source_type) 열을 표시하는데, 환자용 API는 source_type을 내려주지
// 않는다(내부 정보이므로 노출 금지). 개별 검사결과의 표 형태 표시는
// PatientLabResultsTable이 이미 담당하므로, 여기서는 그래프/단일 카드만
// 재사용한다.
export default function PatientLabTrendGroupView({ group }: { group: PatientLabTrendGroup }) {
  const { points, test_name: testName, unit } = group;
  if (points.length === 0) return null;

  return (
    <div>
      <h3>
        <TermOrPlainText text={testName} /> ({unit})
      </h3>
      <Card>
        {points.length === 1 ? (
          <SingleResultCard point={toPresentationPoint(points[0])} testName={testName} />
        ) : (
          <TrendChart points={points.map(toPresentationPoint)} unit={unit} />
        )}
      </Card>
    </div>
  );
}
