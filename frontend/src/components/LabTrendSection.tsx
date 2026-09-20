import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { getPatientLabTrends, LabTrendGroup } from "../api/labTrends";
import { LabTrendPointsView } from "./labTrend/LabTrendPresentation";
import SectionCard from "./ui/SectionCard";
import FormField from "./ui/FormField";
import AlertBox from "./ui/AlertBox";
import EmptyState from "./ui/EmptyState";
import LoadingState from "./ui/LoadingState";
import ErrorState from "./ui/ErrorState";

type LoadState = "loading" | "success" | "forbidden" | "notFound" | "error";

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
    <SectionCard title="검사 추세">
      <p>이 섹션의 그래프와 표는 합성(가짜) 교육용 데이터와 데모 참고범위를 사용합니다.</p>
      <p>이 그래프는 진단이나 예측을 수행하지 않으며, AI가 추세를 해석하지 않습니다.</p>

      {state === "loading" && <LoadingState label="검사 추세를 불러오는 중..." />}

      {state === "forbidden" && (
        <AlertBox variant="error" role="alert">
          검사 추세를 조회할 권한이 없습니다.
        </AlertBox>
      )}

      {state === "notFound" && (
        <AlertBox variant="error" role="alert">
          환자를 찾을 수 없습니다.
        </AlertBox>
      )}

      {state === "error" && (
        <ErrorState
          title="검사 추세를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
          onRetry={loadTrends}
        />
      )}

      {state === "success" && trends.length === 0 && (
        <EmptyState title="표시할 검사결과가 없습니다." />
      )}

      {state === "success" && trends.length > 0 && (
        <div className="page-stack">
          <FormField label="검사 항목 선택" htmlFor="lab-trend-select">
            <select
              id="lab-trend-select"
              value={selectedKey ?? ""}
              onChange={(e) => setSelectedKey(e.target.value)}
            >
              {trends.map((group) => (
                <option key={groupKey(group)} value={groupKey(group)}>
                  {group.test_name} ({group.unit})
                </option>
              ))}
            </select>
          </FormField>

          {selectedGroup && (
            <LabTrendPointsView
              points={selectedGroup.points}
              unit={selectedGroup.unit}
              testName={selectedGroup.test_name}
            />
          )}
        </div>
      )}
    </SectionCard>
  );
}
