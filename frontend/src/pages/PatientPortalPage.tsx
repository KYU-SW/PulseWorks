import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function PatientPortalPage() {
  const { role, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div>
      <h1>환자 포털</h1>
      <p>로그인 역할: {role}</p>
      <p>의료진이 승인한 검사결과와 AI 요약은 이후 작업에서 이 화면에 채워집니다.</p>
      <button onClick={handleLogout}>로그아웃</button>
    </div>
  );
}
