import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { apiPost, clearStoredToken, getStoredToken, setStoredToken } from "../api/client";

export type Role = "DOCTOR" | "NURSE" | "ADMIN_STAFF" | "SYSTEM_ADMIN" | "PATIENT";

type LoginResponse = { access_token: string; token_type: string };

type JwtPayload = { sub: string; role: Role; exp: number };

type AuthState = {
  isAuthenticated: boolean;
  role: Role | null;
  login: (email: string, password: string) => Promise<Role>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

// JWT를 서명 검증 없이 payload만 읽는다 — 이건 화면 이동을 위한 힌트일 뿐이고,
// 실제 접근권한 검증은 항상 백엔드가 다시 한다 (프론트 라우팅은 보안 경계가
// 아니라 UX 편의다).
function decodeJwtPayload(token: string): JwtPayload | null {
  try {
    const [, payloadSegment] = token.split(".");
    const json = atob(payloadSegment.replace(/-/g, "+").replace(/_/g, "/"));
    const payload = JSON.parse(json) as JwtPayload;
    if (!payload.role || !payload.exp) return null;
    return payload;
  } catch {
    return null;
  }
}

function isExpired(payload: JwtPayload): boolean {
  return payload.exp * 1000 <= Date.now();
}

// 새로고침 시 로그인 상태 유지: sessionStorage에 남은 토큰이 있고 아직
// 만료/변조되지 않았으면 그 role을 초기값으로 쓰고, 그렇지 않으면 정리한다.
// useEffect가 아니라 초기 state 계산 자체에서 동기적으로 처리해야 한다 —
// 그렇지 않으면 첫 렌더는 "미인증"으로 그려지고, 보호 라우트가 그 첫 렌더에서
// 이미 /login으로 리다이렉트해버려 나중에 useEffect가 상태를 고쳐도 늦는다.
function readInitialAuthState(): { role: Role | null; isAuthenticated: boolean } {
  const existingToken = getStoredToken();
  if (!existingToken) {
    return { role: null, isAuthenticated: false };
  }
  const payload = decodeJwtPayload(existingToken);
  if (!payload || isExpired(payload)) {
    clearStoredToken();
    return { role: null, isAuthenticated: false };
  }
  return { role: payload.role, isAuthenticated: true };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRole] = useState<Role | null>(() => readInitialAuthState().role);
  const [isAuthenticated, setIsAuthenticated] = useState(() => readInitialAuthState().isAuthenticated);

  function clearSession() {
    clearStoredToken();
    setRole(null);
    setIsAuthenticated(false);
  }

  // API가 401을 반환하면(client.ts가 감지) 로그인 상태를 초기화한다.
  useEffect(() => {
    function handleUnauthorized() {
      clearSession();
    }
    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, []);

  async function login(email: string, password: string): Promise<Role> {
    const response = await apiPost<LoginResponse>("/auth/login", { email, password });
    const payload = decodeJwtPayload(response.access_token);
    if (!payload) {
      throw new Error("서버로부터 유효하지 않은 토큰을 받았습니다.");
    }
    setStoredToken(response.access_token);
    setRole(payload.role);
    setIsAuthenticated(true);
    return payload.role;
  }

  function logout() {
    clearSession();
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, role, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
