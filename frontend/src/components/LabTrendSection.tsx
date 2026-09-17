import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../api/client";
import {
  getPatientLabTrends,
  LabTrendGroup,
  LabTrendPoint,
  LabTrendStatus,
} from "../api/labTrends";

type LoadState = "loading" | "success" | "forbidden" | "notFound" | "error";

const STATUS_LABELS: Record<LabTrendStatus, string> = {
  LOW: "낮음",
  NORMAL: "정상",
  HIGH: "높음",
  UNKNOWN: "판정불가",
};

// 색상은 보조 수단일 뿐이다 — 위 STATUS_LABELS 텍스트가 항상 함께 표시되어
// 색을 구분하지 못해도 판정 상태를 알 수 있어야 한다.
const STATUS_COLORS: Record<LabTrendStatus, string> = {
  LOW: "#2563eb",
  NORMAL: "#16a34a",
  HIGH: "#dc2626",
  UNKNOWN: "#6b7280",
};

const SOURCE_TYPE_LABELS: Record<string, string> = {
  PATIENT_REPORTED: "환자 입력",
  INSTITUTION_GENERATED: "의료기관 생성",
};

// 우선 지원 검사명 — 존재하면 기본 선택 순위로 사용한다. 목록에 없는
// 검사명도 그룹이 있으면 선택지에 포함되고 그래프/표가 동일하게 동작한다.
const PREFERRED_TEST_ORDER = ["HbA1c", "Fasting Glucose"];

function groupKey(group: LabTrendGroup): string {
  return `${group.test_name}|${group.unit}`;
}

function pickDefaultGroup(trends: LabTrendGroup[]): LabTrendGroup {
  for (const preferred of PREFERRED_TEST_ORDER) {
    const found = trends.find((group) => group.test_name === preferred);
    if (found) return found;
  }
  return trends[0];
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

// 단일 검사 항목의 선 그래프 — 점이 2개 이상일 때만 사용한다(한 점만 있는
// 데이터를 추세로 표현하지 않는다). 순수 SVG로 직접 그린다: 이 규모의
// 데모(검사 1개당 점 몇 개)에는 차트 라이브러리를 추가하는 비용이 더 크다고
// 판단했다 — 근거는 완료 보고서에 기록한다.
function TrendChart({ points, unit }: { points: LabTrendPoint[]; unit: string }) {
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
            fill={STATUS_COLORS[p.status]}
          />
          <text
            x={xForIndex(i)}
            y={yForValue(p.value) - 10}
            fontSize={11}
            textAnchor="middle"
            fill="#111827"
          >
            {STATUS_LABELS[p.status]}
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

function SingleResultCard({ point, testName }: { point: LabTrendPoint; testName: string }) {
  return (
    <div>
      <p>
        <strong>{testName}</strong> — 측정값 1건 (추세 표시 없음, 단일 결과)
      </p>
      <p>
        {formatDateTime(point.measured_at)} — {point.value}
        {point.unit} (참고범위 {point.reference_low}-{point.reference_high}
        {point.unit}) — 판정: <strong>{STATUS_LABELS[point.status]}</strong>
      </p>
    </div>
  );
}

function TrendTable({ points }: { points: LabTrendPoint[] }) {
  return (
    <table>
      <thead>
        <tr>
          <th>측정 시각</th>
          <th>값</th>
          <th>단위</th>
          <th>참고범위</th>
          <th>판정</th>
          <th>자료 출처</th>
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
            <td>{STATUS_LABELS[point.status]}</td>
            <td>{SOURCE_TYPE_LABELS[point.source_type] ?? point.source_type}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function LabTrendSection({ patientId }: { patientId: string | number }) {
  const [state, setState] = useState<LoadState>("loading");
  const [trends, setTrends] = useState<LabTrendGroup[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const hasFetchedRef = useRef<string | number | null>(null);

  async function loadTrends() {
    setState("loading");
    try {
      const result = await getPatientLabTrends(patientId);
      setTrends(result.trends);
      if (result.trends.length > 0) {
        setSelectedKey(groupKey(pickDefaultGroup(result.trends)));
      }
      setState("success");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) return; // client.ts가 로그아웃 처리
        if (err.status === 403) {
          setState("forbidden");
          return;
        }
        if (err.status === 404) {
          setState("notFound");
          return;
        }
      }
      setState("error");
    }
  }

  useEffect(() => {
    if (hasFetchedRef.current === patientId) return;
    hasFetchedRef.current = patientId;
    loadTrends();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId]);

  const selectedGroup = useMemo(
    () => trends.find((group) => groupKey(group) === selectedKey) ?? null,
    [trends, selectedKey]
  );

  return (
    <section>
      <h2>검사 추세</h2>
      <p>이 섹션의 그래프와 표는 합성(가짜) 교육용 데이터와 데모 참고범위를 사용합니다.</p>
      <p>이 그래프는 진단이나 예측을 수행하지 않으며, AI가 추세를 해석하지 않습니다.</p>

      {state === "loading" && <p>검사 추세를 불러오는 중...</p>}

      {state === "forbidden" && <p role="alert">검사 추세를 조회할 권한이 없습니다.</p>}

      {state === "notFound" && <p role="alert">환자를 찾을 수 없습니다.</p>}

      {state === "error" && (
        <div>
          <p role="alert">검사 추세를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
          <button onClick={loadTrends}>다시 시도</button>
        </div>
      )}

      {state === "success" && trends.length === 0 && <p>표시할 검사결과가 없습니다.</p>}

      {state === "success" && trends.length > 0 && (
        <div>
          <label>
            검사 항목 선택{" "}
            <select
              value={selectedKey ?? ""}
              onChange={(e) => setSelectedKey(e.target.value)}
            >
              {trends.map((group) => (
                <option key={groupKey(group)} value={groupKey(group)}>
                  {group.test_name} ({group.unit})
                </option>
              ))}
            </select>
          </label>

          {selectedGroup && selectedGroup.points.length === 1 && (
            <SingleResultCard point={selectedGroup.points[0]} testName={selectedGroup.test_name} />
          )}

          {selectedGroup && selectedGroup.points.length >= 2 && (
            <>
              <TrendChart points={selectedGroup.points} unit={selectedGroup.unit} />
              <TrendTable points={selectedGroup.points} />
            </>
          )}
        </div>
      )}
    </section>
  );
}
