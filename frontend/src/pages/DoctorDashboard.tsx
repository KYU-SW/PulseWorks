import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { AssignedPatient, getAssignedPatients } from "../api/patients";

type LoadState = "loading" | "success" | "forbidden" | "error";

export default function DoctorDashboard() {
  const { role, logout } = useAuth();
  const navigate = useNavigate();
  const [patients, setPatients] = useState<AssignedPatient[]>([]);
  const [state, setState] = useState<LoadState>("loading");
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
    <div>
      <h1>의료진 대시보드</h1>
      <p>로그인 역할: {role}</p>
      <p>이 화면의 모든 환자 데이터는 합성(가짜) 교육용 데이터입니다.</p>

      {state === "loading" && <p>담당 환자 목록을 불러오는 중...</p>}

      {state === "forbidden" && (
        <p role="alert">담당 환자 목록을 조회할 권한이 없습니다.</p>
      )}

      {state === "error" && (
        <div>
          <p role="alert">담당 환자 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
          <button onClick={loadPatients}>다시 시도</button>
        </div>
      )}

      {state === "success" && patients.length === 0 && (
        <p>현재 배정된 환자가 없습니다.</p>
      )}

      {state === "success" && patients.length > 0 && (
        <ul>
          {patients.map((patient) => (
            <li key={patient.id}>
              {patient.name} ({patient.mrn}) — 생년월일 {patient.birth_date} —{" "}
              {patient.assignment_role}{" "}
              <Link to={`/doctor/patients/${patient.id}`}>상세보기</Link>
            </li>
          ))}
        </ul>
      )}

      <button onClick={handleLogout}>로그아웃</button>
    </div>
  );
}
