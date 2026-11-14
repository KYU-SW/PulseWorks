import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { AssignedPatient, getAssignedPatients } from "../api/patients";
import AppShell from "../components/ui/AppShell";
import AppHeader from "../components/ui/AppHeader";
import Navigation from "../components/ui/Navigation";
import PageHeader from "../components/ui/PageHeader";
import Card from "../components/ui/Card";
import LinkButton from "../components/ui/LinkButton";
import LoadingState from "../components/ui/LoadingState";
import EmptyState from "../components/ui/EmptyState";
import ErrorState from "../components/ui/ErrorState";
import AlertBox from "../components/ui/AlertBox";
import FormField from "../components/ui/FormField";

type LoadState = "loading" | "success" | "forbidden" | "error";

// UX-1A: 이미 authorization을 거쳐 내려온 담당 환자 목록만 대상으로 하는
// client-side 검색이다 — 서버에 쿼리를 보내지 않으므로 권한 범위를 넘지
// 않는다. 이름/MRN 부분 일치, 대소문자 무시, 양끝 공백 무시만 한다(오타
// 보정/fuzzy 검색 없음).
function filterAssignedPatients(patients: AssignedPatient[], query: string): AssignedPatient[] {
  const normalizedQuery = query.trim().toLocaleLowerCase();
  if (normalizedQuery === "") {
    return patients;
  }
  return patients.filter((patient) => {
    const name = patient.name.toLocaleLowerCase();
    const mrn = patient.mrn.toLocaleLowerCase();
    return name.includes(normalizedQuery) || mrn.includes(normalizedQuery);
  });
}

export default function DoctorDashboard() {
  const { role, logout } = useAuth();
  const navigate = useNavigate();
  const [patients, setPatients] = useState<AssignedPatient[]>([]);
  const [state, setState] = useState<LoadState>("loading");
  const [searchQuery, setSearchQuery] = useState("");
  // StrictMode(개발 모드)에서 effect가 두 번 실행돼도 요청이 중복되지 않도록
  // 한다 — 실제 운영 빌드에서는 어차피 한 번만 실행되지만, 명시적으로 막는다.
  const hasFetchedRef = useRef(false);

  async function loadPatients() {
    setState("loading");
    try {
      const data = await getAssignedPatients();
      setPatients(data);
      setState("success");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          // client.ts가 이미 세션을 정리하고 auth:unauthorized를 쏘아
          // AuthContext가 로그아웃 상태로 만들고, ProtectedRoute가
          // /login으로 보낸다 — 여기서 별도로 에러를 보여줄 필요 없다.
          return;
        }
        if (err.status === 403) {
          setState("forbidden");
          return;
        }
      }
      // 서버의 내부 오류 내용은 그대로 노출하지 않고, 민감정보 없는
      // 일반적인 메시지만 보여준다.
      setState("error");
    }
  }

  useEffect(() => {
    if (hasFetchedRef.current) return;
    hasFetchedRef.current = true;
    loadPatients();
  }, []);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <AppShell
      header={
        <AppHeader brand="EMR 프로토타입">
          <Navigation role={role!} onLogout={handleLogout} />
        </AppHeader>
      }
    >
      <PageHeader title="의료진 대시보드" description={`로그인 역할: ${role}`} />
      <p>이 화면의 모든 환자 데이터는 합성(가짜) 교육용 데이터입니다.</p>

      {state === "loading" && <LoadingState label="담당 환자 목록을 불러오는 중..." />}

      {state === "forbidden" && (
        <AlertBox variant="error" role="alert">
          담당 환자 목록을 조회할 권한이 없습니다.
        </AlertBox>
      )}

      {state === "error" && (
        <ErrorState
          title="담당 환자 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요."
          onRetry={loadPatients}
        />
      )}

      {state === "success" && patients.length === 0 && (
        <EmptyState title="현재 배정된 환자가 없습니다." />
      )}

      {state === "success" && patients.length > 0 && (
        <>
          <FormField label="환자 이름 또는 MRN 검색" htmlFor="patient-search">
            <input
              id="patient-search"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="환자 이름 또는 MRN 검색"
            />
          </FormField>

          {(() => {
            const filteredPatients = filterAssignedPatients(patients, searchQuery);
            const hasQuery = searchQuery.trim() !== "";
            return (
              <>
                {hasQuery && <p aria-live="polite">검색 결과 {filteredPatients.length}명</p>}

                {filteredPatients.length === 0 ? (
                  <EmptyState title="검색 조건에 맞는 담당 환자가 없습니다." />
                ) : (
                  <ul className="page-grid">
                    {filteredPatients.map((patient) => (
                      <li key={patient.id}>
                        <Card>
                          <p>
                            {patient.name} ({patient.mrn})
                          </p>
                          <p>
                            생년월일 {patient.birth_date} — {patient.assignment_role}
                          </p>
                          <LinkButton to={`/doctor/patients/${patient.id}`} variant="secondary">
                            상세보기
                          </LinkButton>
                        </Card>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            );
          })()}
        </>
      )}
    </AppShell>
  );
}
