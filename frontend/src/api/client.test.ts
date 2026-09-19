import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, apiGet, apiPatch, apiPost, clearStoredToken, setStoredToken } from "./client";

function mockFetchOnce(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

describe("api client", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  // 11. API 요청에 Bearer Token 포함
  it("attaches the stored token as a Bearer header", async () => {
    setStoredToken("test-token-value");
    const fetchMock = mockFetchOnce(200, { ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await apiGet("/some/protected/resource");

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer test-token-value");
  });

  it("does not attach an Authorization header when there is no stored token", async () => {
    clearStoredToken();
    const fetchMock = mockFetchOnce(200, { ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await apiPost("/auth/login", { email: "a@example.test", password: "x" });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.headers.Authorization).toBeUndefined();
  });

  // 12. API 401 응답 시 로그인 상태 초기화
  it("clears the stored token and dispatches auth:unauthorized on a 401", async () => {
    setStoredToken("stale-token");
    const fetchMock = mockFetchOnce(401, { detail: "Invalid token" });
    vi.stubGlobal("fetch", fetchMock);

    const listener = vi.fn();
    window.addEventListener("auth:unauthorized", listener);

    await expect(apiGet("/patients/assigned")).rejects.toBeInstanceOf(ApiError);

    expect(sessionStorage.getItem("access_token")).toBeNull();
    expect(listener).toHaveBeenCalledTimes(1);

    window.removeEventListener("auth:unauthorized", listener);
  });

  it("surfaces the server's error detail for non-401 failures", async () => {
    const fetchMock = mockFetchOnce(500, { detail: "boom" });
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiGet("/whatever")).rejects.toMatchObject({ status: 500, message: "boom" });
  });

  it("sends a PATCH request with a JSON body and the Bearer token", async () => {
    setStoredToken("test-token-value");
    const fetchMock = mockFetchOnce(200, { ok: true });
    vi.stubGlobal("fetch", fetchMock);

    await apiPatch("/reports/1", { narrative: "x" });

    const [, options] = fetchMock.mock.calls[0];
    expect(options.method).toBe("PATCH");
    expect(JSON.parse(options.body)).toEqual({ narrative: "x" });
    expect(options.headers.Authorization).toBe("Bearer test-token-value");
  });
});
