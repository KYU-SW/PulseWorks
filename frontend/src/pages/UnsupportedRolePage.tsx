import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

// NURSE / ADMIN_STAFF / SYSTEM_ADMIN 로그인용 안전한 fallback. 의사·환자
// 화면으로 보내지 않고, 환자 임상정보는 전혀 표시하지 않는다.
export default function UnsupportedRolePage() {
  const { role, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div>
      <h1>준비 중인 화면입니다</h1>
      <p>로그인 역할: {role}</p>
      <p>이 역할({role})을 위한 화면은 아직 지원되지 않습니다. 추후 업데이트를 기다려 주세요.</p>
      <button onClick={handleLogout}>로그아웃</button>
    </div>
  );
}
