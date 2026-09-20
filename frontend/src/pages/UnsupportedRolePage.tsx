import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/ui/AppShell";
import AppHeader from "../components/ui/AppHeader";
import Navigation from "../components/ui/Navigation";
import PageHeader from "../components/ui/PageHeader";
import AlertBox from "../components/ui/AlertBox";

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
    <AppShell
      header={
        <AppHeader brand="EMR 프로토타입">
          <Navigation role={role!} onLogout={handleLogout} />
        </AppHeader>
      }
    >
      <PageHeader title="준비 중인 화면입니다" description={`로그인 역할: ${role}`} />
      <AlertBox variant="info">
        이 역할({role})을 위한 화면은 아직 지원되지 않습니다. 추후 업데이트를 기다려 주세요.
      </AlertBox>
    </AppShell>
  );
}
