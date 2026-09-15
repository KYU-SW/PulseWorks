export function makeFakeJwt(role: string, expiresInSeconds = 3600): string {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const payload = btoa(
    JSON.stringify({ sub: "1", role, exp: Math.floor(Date.now() / 1000) + expiresInSeconds })
  );
  return `${header}.${payload}.fake-signature-not-a-real-jwt`;
}
