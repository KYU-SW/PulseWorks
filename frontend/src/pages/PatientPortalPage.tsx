import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import AppShell from "../components/ui/AppShell";
import AppHeader from "../components/ui/AppHeader";
import Navigation from "../components/ui/Navigation";
import PageHeader from "../components/ui/PageHeader";
import Card from "../components/ui/Card";
import LinkButton from "../components/ui/LinkButton";

export default function PatientPortalPage() {
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
      <PageHeader title="환자 포털" description={`로그인 역할: ${role}`} />
      <Card>
        <p>담당 의료진이 승인한 보고서를 확인할 수 있습니다.</p>
        <LinkButton to="/patient/reports" variant="primary">
          승인된 보고서 보기
        </LinkButton>
      </Card>
    </AppShell>
  );
}
