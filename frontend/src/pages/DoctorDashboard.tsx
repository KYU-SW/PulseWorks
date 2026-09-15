import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function DoctorDashboard() {
  const { role, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div>
      <h1>의료진 대시보드</h1>
      <p>로그인 역할: {role}</p>
      <p>담당 환자 목록과 진료과별 대시보드는 이후 작업에서 이 화면에 채워집니다.</p>
      <button onClick={handleLogout}>로그아웃</button>
    </div>
  );
}
