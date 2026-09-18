// Task 11의 LabTrendSection(자체 fetch, status: LabTrendStatus 리터럴
// 유니언)과 Task 14의 보고서 LabTrendsSection(저장된 스냅샷, status:
// string — 백엔드 Pydantic 스키마를 그대로 미러링해 리터럴로 좁히지
// 않음)이 이 파일의 순수 표시 컴포넌트를 함께 쓴다. 두 타입 모두 이
// 최소 인터페이스를 구조적으로 만족하도록 status를 string으로 받는다.
export type LabTrendPresentationPoint = {
  value: number;
  unit: string;
  reference_low: number;
  reference_high: number;
  measured_at: string;
  status: string;
  rule_id: string;
  encounter_id: number;
  source_type: string;
};

export const STATUS_LABELS: Record<string, string> = {
  LOW: "낮음",
  NORMAL: "정상",
  HIGH: "높음",
  UNKNOWN: "판정불가",
};

// 색상은 보조 수단일 뿐이다 — 위 STATUS_LABELS 텍스트가 항상 함께 표시되어
// 색을 구분하지 못해도 판정 상태를 알 수 있어야 한다.
const STATUS_COLORS: Record<string, string> = {
  LOW: "#2563eb",
  NORMAL: "#16a34a",
  HIGH: "#dc2626",
  UNKNOWN: "#6b7280",
};

function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

function statusColor(status: string): string {
  return STATUS_COLORS[status] ?? STATUS_COLORS.UNKNOWN;
}

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  PATIENT_REPORTED: "환자 입력",
  INSTITUTION_GENERATED: "의료기관 생성",
};

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

// 단일 검사 항목의 선 그래프 — 점이 2개 이상일 때만 사용한다(한 점만 있는
// 데이터를 추세로 표현하지 않는다). 순수 SVG로 직접 그린다: 이 규모의
// 데모(검사 1개당 점 몇 개)에는 차트 라이브러리를 추가하는 비용이 더 크다고
// 판단했다(Task 11 완료 보고서 참고).
export function TrendChart({ points, unit }: { points: LabTrendPresentationPoint[]; unit: string }) {
  const width = 640;
  const height = 220;
  const padding = { top: 20, right: 24, bottom: 36, left: 48 };

  const referenceLow = points[0].reference_low;
  const referenceHigh = points[0].reference_high;
  const sameReferenceRange = points.every(
    (p) => p.reference_low === referenceLow && p.reference_high === referenceHigh
  );

  const values = points.map((p) => p.value);
  const minValue = Math.min(...values, sameReferenceRange ? referenceLow : Math.min(...values));
  const maxValue = Math.max(...values, sameReferenceRange ? referenceHigh : Math.max(...values));
  const valueSpan = maxValue - minValue || 1;

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  function xForIndex(index: number): number {
    if (points.length === 1) return padding.left + plotWidth / 2;
    return padding.left + (plotWidth * index) / (points.length - 1);
  }

  function yForValue(value: number): number {
    return padding.top + plotHeight - ((value - minValue) / valueSpan) * plotHeight;
  }

  const linePath = points
    .map((p, i) => `${i === 0 ? "M" : "L"}${xForIndex(i)},${yForValue(p.value)}`)
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`검사값 추세 그래프 (단위: ${unit})`}
      style={{ width: "100%", maxWidth: `${width}px`, height: "auto" }}
    >
      {sameReferenceRange && (
        <rect
          x={padding.left}
          y={yForValue(referenceHigh)}
          width={plotWidth}
          height={Math.max(yForValue(referenceLow) - yForValue(referenceHigh), 0)}
          fill="#16a34a"
          opacity={0.08}
        />
      )}
      <line
        x1={padding.left}
        y1={padding.top + plotHeight}
        x2={padding.left + plotWidth}
        y2={padding.top + plotHeight}
        stroke="#9ca3af"
      />
      <path d={linePath} fill="none" stroke="#374151" strokeWidth={1.5} />
      {points.map((p, i) => (
        <g key={`${p.measured_at}-${i}`}>
          <circle
            cx={xForIndex(i)}
            cy={yForValue(p.value)}
            r={5}
            fill={statusColor(p.status)}
          />
          <text
            x={xForIndex(i)}
            y={yForValue(p.value) - 10}
            fontSize={11}
            textAnchor="middle"
            fill="#111827"
          >
            {statusLabel(p.status)}
          </text>
          <text
            x={xForIndex(i)}
            y={height - padding.bottom + 16}
            fontSize={10}
            textAnchor="middle"
            fill="#4b5563"
          >
            {new Date(p.measured_at).toLocaleDateString()}
          </text>
        </g>
      ))}
    </svg>
  );
}

export function SingleResultCard({ point, testName }: { point: LabTrendPresentationPoint; testName: string }) {
  return (
    <div>
      <p>
        <strong>{testName}</strong> — 측정값 1건 (추세 표시 없음, 단일 결과)
      </p>
      <p>
        {formatDateTime(point.measured_at)} — {point.value}
        {point.unit} (참고범위 {point.reference_low}-{point.reference_high}
        {point.unit}) — 판정: <strong>{statusLabel(point.status)}</strong>
      </p>
    </div>
  );
}

export function TrendTable({ points }: { points: LabTrendPresentationPoint[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th scope="col">측정 시각</th>
          <th scope="col">값</th>
          <th scope="col">단위</th>
          <th scope="col">참고범위</th>
          <th scope="col">판정</th>
          <th scope="col">자료 출처</th>
        </tr>
      </thead>
      <tbody>
        {points.map((point, index) => (
          <tr key={`${point.measured_at}-${index}`}>
            <td>{formatDateTime(point.measured_at)}</td>
            <td>{point.value}</td>
            <td>{point.unit}</td>
            <td>
              {point.reference_low}-{point.reference_high}
            </td>
            <td>{statusLabel(point.status)}</td>
            <td>{SOURCE_TYPE_LABELS[point.source_type] ?? point.source_type}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// 점 개수에 따라 단일 결과 카드 또는 그래프+표를 고르는 조합 컴포넌트 —
// 이 분기 로직 자체도 두 곳(LabTrendSection, LabTrendsSection)에서
// 중복하지 않도록 여기 하나만 둔다.
export function LabTrendPointsView({
  points,
  unit,
  testName,
}: {
  points: LabTrendPresentationPoint[];
  unit: string;
  testName: string;
}) {
  if (points.length === 0) return null;
  if (points.length === 1) {
    return <SingleResultCard point={points[0]} testName={testName} />;
  }
  return (
    <>
      <TrendChart points={points} unit={unit} />
      <TrendTable points={points} />
    </>
  );
}
