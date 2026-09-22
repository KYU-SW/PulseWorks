from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ALLOWED_ORIGIN = "http://localhost:5173"
DISALLOWED_ORIGIN = "http://evil.example.test"


# 1. OPTIONS /auth/login (preflight) 요청이 성공하는지 + 허용 Origin에
#    Access-Control-Allow-Origin이 정확히 반환되는지
def test_preflight_from_allowed_origin_succeeds_with_correct_header():
    response = client.options(
        "/auth/login",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_actual_request_from_allowed_origin_gets_cors_header():
    response = client.get("/health", headers={"Origin": ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN


# 3. 허용되지 않은 Origin에는 CORS 허용 헤더가 반환되지 않는지
def test_disallowed_origin_gets_no_cors_header():
    response = client.get("/health", headers={"Origin": DISALLOWED_ORIGIN})

    # 서버 자체는 여전히 200을 주지만(브라우저가 막는 건 origin 헤더 부재로
    # 판단하는 거지, 서버가 요청을 거부하는 게 아니다), CORS 허용 헤더는 없어야
    # 한다 — 브라우저가 이 헤더 부재를 보고 스크립트에 응답을 넘기지 않는다.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers.keys()}


def test_preflight_from_disallowed_origin_gets_no_cors_header():
    response = client.options(
        "/auth/login",
        headers={
            "Origin": DISALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert "access-control-allow-origin" not in {k.lower() for k in response.headers.keys()}


def test_allow_credentials_is_disabled():
    response = client.options(
        "/auth/login",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert "access-control-allow-credentials" not in {k.lower() for k in response.headers.keys()}


# PATCH preflight (보고서 저장 시 실제로 브라우저가 보내는 요청) 회귀 —
# allow_methods에 PATCH가 빠져 있으면 CORSMiddleware가 이 요청을 400으로
# 거부한다("Disallowed CORS method").
def test_patch_preflight_from_allowed_origin_succeeds_with_patch_in_allow_methods():
    response = client.options(
        "/reports/1",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )

    assert response.status_code < 300
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    allowed_methods = {m.strip() for m in response.headers["access-control-allow-methods"].split(",")}
    assert "PATCH" in allowed_methods
    # 기존 허용 메서드는 그대로 유지된다.
    assert {"GET", "POST", "OPTIONS"}.issubset(allowed_methods)


def test_patch_preflight_still_allows_authorization_and_content_type_headers():
    response = client.options(
        "/reports/1",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )

    allowed_headers = {h.strip().lower() for h in response.headers["access-control-allow-headers"].split(",")}
    assert "authorization" in allowed_headers
    assert "content-type" in allowed_headers


def test_patch_preflight_from_disallowed_origin_gets_no_cors_header():
    response = client.options(
        "/reports/1",
        headers={
            "Origin": DISALLOWED_ORIGIN,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "authorization, content-type",
        },
    )

    assert "access-control-allow-origin" not in {k.lower() for k in response.headers.keys()}
