import { Link, useNavigate } from "react-router-dom";
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
      <p>
        <Link to="/patient/reports">승인된 보고서 보기</Link>
      </p>
      <button onClick={handleLogout}>로그아웃</button>
    </div>
  );
}
