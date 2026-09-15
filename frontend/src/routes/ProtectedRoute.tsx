import { Navigate } from "react-router-dom";
import { Role, useAuth } from "../auth/AuthContext";

// 이건 사용자 경험을 위한 라우트 보호일 뿐이다 — 실제 데이터 접근권한은
// 항상 보호된 API 쪽에서 백엔드가 (get_current_user/require_roles/
// can_access_patient로) 다시 확인한다. 프론트엔드 라우팅만으로 보안이
// 보장된다고 간주하지 않는다.
export default function ProtectedRoute({
  allowedRoles,
  children,
}: {
  allowedRoles: Role[];
  children: JSX.Element;
}) {
  const { isAuthenticated, role } = useAuth();

  if (!isAuthenticated || role === null) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(role)) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
