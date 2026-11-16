import { Link } from "react-router-dom";
import { Role } from "../../auth/AuthContext";

type NavLink = { to: string; label: string };

const DOCTOR_LINKS: NavLink[] = [
  { to: "/doctor", label: "대시보드" },
  { to: "/doctor/reports", label: "진료 보고서" },
];
const PATIENT_LINKS: NavLink[] = [
  { to: "/patient", label: "포털" },
  { to: "/patient/reports", label: "승인된 보고서" },
];

interface NavigationProps {
  role: Role;
  onLogout: () => void;
}

// 순수 프레젠테이션 컴포넌트 — useAuth()를 직접 호출하지 않고 role/
// onLogout을 props로 받는다. 호출부가 기존 useAuth()의 role과 logout을
// 그대로 넘기면 된다(새 인증 로직·토큰 저장소를 만들지 않음). 여기 보이는
// 링크는 UX 편의일 뿐, 실제 접근제어는 ProtectedRoute와 백엔드가 한다.
export default function Navigation({ role, onLogout }: NavigationProps) {
  const links = role === "DOCTOR" ? DOCTOR_LINKS : role === "PATIENT" ? PATIENT_LINKS : [];

  return (
    <nav className="app-navigation" aria-label="주요 내비게이션">
      <ul className="app-navigation__list">
        {links.map((link) => (
          <li key={link.to}>
            <Link className="app-navigation__link" to={link.to}>
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
      <button type="button" onClick={onLogout}>
        로그아웃
      </button>
    </nav>
  );
}
