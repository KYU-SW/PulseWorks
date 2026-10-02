// 중앙 API client — API 주소를 여러 파일에 하드코딩하지 않고 Vite 환경변수
// (VITE_API_BASE_URL)로 한 곳에서만 관리한다. 브라우저에서는 항상
// http://localhost:8000처럼 호스트에 게시된 주소를 쓰며, Docker Compose
// 내부 서비스 주소(http://backend:8000)는 브라우저 코드에서 절대 쓰지 않는다
// (브라우저는 그 호스트명을 해석할 수 없다).
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const TOKEN_STORAGE_KEY = "access_token";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function getStoredToken(): string | null {
  return sessionStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  sessionStorage.removeItem(TOKEN_STORAGE_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((options.headers as Record<string, string>) ?? {}),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    // 인증이 더 이상 유효하지 않다는 뜻 — 로그인 상태를 초기화하고, AuthContext가
    // 이를 감지해 화면을 로그인 페이지로 되돌릴 수 있도록 이벤트를 알린다.
    // (토큰 자체는 절대 로그하지 않는다.)
    clearStoredToken();
    window.dispatchEvent(new Event("auth:unauthorized"));
    throw new ApiError(401, "Unauthorized");
  }

  if (!response.ok) {
    let detail = "요청을 처리할 수 없습니다.";
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // 응답 본문이 JSON이 아니면 기본 메시지를 그대로 쓴다.
    }
    throw new ApiError(response.status, detail);
  }

  return (await response.json()) as T;
}

export function apiGet<T>(path: string): Promise<T> {
  return request<T>(path, { method: "GET" });
}

// init은 fetch에 추가로 전달할 선택적 옵션(예: AbortSignal)이다. 기존
// 호출부(init 생략)는 그대로 동작한다 — 이 매개변수는 하위 호환
// 추가일 뿐, 다른 요청(승인·반려·저장 등)의 동작을 바꾸지 않는다.
export function apiPost<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
  return request<T>(path, { method: "POST", body: JSON.stringify(body), ...init });
}

export function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: "PATCH", body: JSON.stringify(body) });
}
