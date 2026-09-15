from fastapi.testclient import TestClient

from app.main import app
from app.models import AuditLog, Role, User
from scripts.seed_synthetic_data import DEMO_PASSWORD, PLACEHOLDER_HASHED_PASSWORD, seed

client = TestClient(app)

DOCTOR_EMAIL = "endocrine.doctor@example.test"


# 1. 올바른 이메일과 비밀번호로 로그인 성공
def test_login_with_correct_credentials_succeeds(db_session, override_get_db):
    seed(db_session)

    response = client.post(
        "/auth/login", json={"email": DOCTOR_EMAIL, "password": DEMO_PASSWORD}
    )

    assert response.status_code == 200


# 2. 잘못된 비밀번호로 로그인 실패
def test_login_with_wrong_password_fails(db_session, override_get_db):
    seed(db_session)

    response = client.post(
        "/auth/login", json={"email": DOCTOR_EMAIL, "password": "wrong-password"}
    )

    assert response.status_code == 401


# 3. 존재하지 않는 이메일로 로그인 실패 — 그리고 "이메일 존재 여부"를 구체적으로
#    노출하지 않는지(문항 2와 동일한 메시지/코드인지)도 함께 확인한다.
def test_login_with_nonexistent_email_fails_without_revealing_which_reason(
    db_session, override_get_db
):
    seed(db_session)

    wrong_password_response = client.post(
        "/auth/login", json={"email": DOCTOR_EMAIL, "password": "wrong-password"}
    )
    nonexistent_email_response = client.post(
        "/auth/login", json={"email": "nobody@example.test", "password": "whatever"}
    )

    assert nonexistent_email_response.status_code == 401
    assert (
        wrong_password_response.status_code == nonexistent_email_response.status_code
    )
    assert wrong_password_response.json() == nonexistent_email_response.json()


# 4. 로그인 응답에 JWT Access Token 존재 (+ hashed_password는 절대 없어야 함, 문항 18)
def test_login_response_includes_access_token_and_never_the_password_hash(
    db_session, override_get_db
):
    seed(db_session)

    response = client.post(
        "/auth/login", json={"email": DOCTOR_EMAIL, "password": DEMO_PASSWORD}
    )

    body = response.json()
    assert "access_token" in body and isinstance(body["access_token"], str) and body["access_token"]
    assert body["token_type"] == "bearer"
    assert "hashed_password" not in body
    assert "password" not in body
    assert "hashed_password" not in response.text


# 5. JWT에서 현재 사용자를 정상 식별
def test_get_current_user_identifies_user_from_valid_token(db_session):
    from app.core.deps import get_current_user
    from app.core.security import create_access_token

    seed(db_session)
    doctor = db_session.query(User).filter_by(email=DOCTOR_EMAIL).first()
    token = create_access_token(subject=str(doctor.id), role=doctor.role.value)

    resolved = get_current_user(authorization=f"Bearer {token}", db=db_session)

    assert resolved.id == doctor.id
    assert resolved.email == DOCTOR_EMAIL


# 6. JWT가 없으면 보호 API 접근 실패
def test_protected_endpoint_without_token_returns_401(auth_test_client):
    response = auth_test_client.get("/protected")
    assert response.status_code in (401, 422)  # FastAPI's required Header() yields 422; both mean "rejected, no auth"


# 7. 잘못된 JWT 접근 실패
def test_protected_endpoint_with_invalid_token_returns_401(auth_test_client):
    response = auth_test_client.get(
        "/protected", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


# 19. 이전 Seed의 placeholder 비밀번호가 남아 있지 않음
def test_seed_replaces_placeholder_password_with_a_real_hash(db_session):
    from app.core.security import verify_password

    seed(db_session)

    users = db_session.query(User).all()
    assert len(users) > 0
    assert all(u.hashed_password != PLACEHOLDER_HASHED_PASSWORD for u in users)
    # 진짜 해시라면 원본 데모 비밀번호로 검증이 성공해야 한다.
    doctor = db_session.query(User).filter_by(email=DOCTOR_EMAIL).first()
    assert verify_password(DEMO_PASSWORD, doctor.hashed_password) is True


# 20. 인증 관련 감사 로그가 필요한 범위에서 기록됨 (로그인 성공 시)
def test_successful_login_writes_audit_log(db_session, override_get_db):
    seed(db_session)
    doctor = db_session.query(User).filter_by(email=DOCTOR_EMAIL).first()

    response = client.post(
        "/auth/login", json={"email": DOCTOR_EMAIL, "password": DEMO_PASSWORD}
    )
    assert response.status_code == 200

    log_entry = (
        db_session.query(AuditLog)
        .filter_by(actor_user_id=doctor.id, action="LOGIN")
        .first()
    )
    assert log_entry is not None
    assert log_entry.resource_type == "Auth"
