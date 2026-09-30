"""POST /reports/{report_id}/generate-narrative의 provider 배선 테스트.

tests/test_generate_narrative_api.py(Task 16)는 건드리지 않는다 - mock
기본값에서 그 파일의 기존 테스트가 전부 수정 없이 통과해야 한다는
요구사항 때문에, 이 새 파일에서 provider 관련 동작(LLM 경로, 설정
오류, 검증 실패 시 DB 무변경)만 별도로 검증한다."""

from datetime import datetime, timezone

import pytest
from app.core.config import Settings
from app.main import app
from app.models import AiSummary, AuditLog, ClinicalReport, Encounter, Patient
from app.services.narrative_providers.base import (
    MentionedMeasurement,
    NarrativeProvider,
    NarrativeProviderResult,
)
from fastapi.testclient import TestClient
from scripts.seed_synthetic_data import seed

client = TestClient(app)

ENDOCRINE_DOCTOR_EMAIL = "endocrine.doctor@example.test"


# Task C2: 이 파일의 테스트가 실제 backend/.env의 NARRATIVE_PROVIDER 값과
# 무관하게 항상 안전한 mock 기본값에서 시작하도록 한다 - 로컬 .env가
# 우연히 llm으로 설정돼 있어도(실제로 이런 일이 있었다) 이 기본값이
# 먼저 적용된다. 개별 테스트가 스스로 factory.get_settings나
# get_narrative_provider를 monkeypatch하면(이 파일의 LLM 경로/설정
# 오류 테스트 대부분이 이미 그렇게 한다) 그 값이 이 기본값을 덮어쓴다 -
# monkeypatch는 같은 테스트 안에서 나중에 설정한 값을 쓰고, teardown
# 시점에는 원래 값으로 복구하므로 서로 충돌하지 않는다.
@pytest.fixture(autouse=True)
def _default_to_mock_settings(monkeypatch):
    monkeypatch.setattr(
        "app.services.narrative_providers.factory.get_settings",
        lambda: Settings(narrative_provider="mock"),
    )


def _login(email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": "demo1234"})
    return response.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _endo_patient(db_session) -> Patient:
    return db_session.query(Patient).filter_by(mrn="SYN-0001").first()


def _first_encounter_id(db_session, patient_id: int) -> int:
    return (
        db_session.query(Encounter)
        .filter_by(patient_id=patient_id)
        .order_by(Encounter.start_time)
        .first()
        .id
    )


def _create_report(token: str, patient_id: int, encounter_id: int) -> dict:
    response = client.post(
        f"/patients/{patient_id}/reports",
        json={
            "report_type": "DOCTOR_REFERENCE",
            "scope_type": "SINGLE_ENCOUNTER",
            "encounter_ids": [encounter_id],
        },
        headers=_auth_header(token),
    )
    return response.json()


def _generate(report_id: int, token: str):
    return client.post(f"/reports/{report_id}/generate-narrative", headers=_auth_header(token))


class _FakeProvider(NarrativeProvider):
    def __init__(self, result: NarrativeProviderResult | None = None, error: Exception | None = None):
        self._result = result
        self._error = error
        self.called = False

    def generate(self, snapshot):
        self.called = True
        if self._error is not None:
            raise self._error
        return self._result


VALID_LLM_RESULT = NarrativeProviderResult(
    narrative="HbA1c 결과가 확인됩니다.",
    cited_record_ids=[],
    # SYN-0001의 1번째 Encounter(2026-03-10)에 실제로 있는 HbA1c 7.2%를
    # 그대로 인용한다 - snapshot.lab_results에 존재해야 검증을 통과한다.
    mentioned_measurements=[MentionedMeasurement("HbA1c", 7.2, "%")],
    provider="LLM",
    model="test-model",
    version="1",
)


def _invalid_llm_result_with_banned_phrase() -> NarrativeProviderResult:
    return NarrativeProviderResult(
        narrative="상태가 악화되었습니다.",
        cited_record_ids=[],
        mentioned_measurements=[],
        provider="LLM",
        model="test-model",
        version="1",
    )


# ============================== 설정 오류 경로 ================================


def test_llm_provider_without_api_key_returns_503_and_writes_nothing(
    db_session, override_get_db, monkeypatch
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    monkeypatch.setattr(
        "app.services.narrative_providers.factory.get_settings",
        lambda: Settings(narrative_provider="llm", llm_api_key=None, llm_model="gpt-4"),
    )
    ai_summary_count_before = db_session.query(AiSummary).count()
    audit_log_count_before = db_session.query(AuditLog).count()

    response = _generate(created["id"], token)

    assert response.status_code == 503
    assert response.json()["detail"] == "설명문 생성 서비스를 사용할 수 없습니다."
    # 내부 오류 코드나 provider 상세를 응답에 노출하지 않는다.
    assert "LLM_API_KEY_MISSING" not in response.text
    assert db_session.query(AiSummary).count() == ai_summary_count_before
    assert db_session.query(AuditLog).count() == audit_log_count_before
    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert report.content["narrative"] is None
    assert report.last_modified_at.replace(tzinfo=timezone.utc) == datetime.fromisoformat(
        created["last_modified_at"]
    ).replace(tzinfo=timezone.utc)


def test_llm_provider_with_key_and_model_still_returns_503_because_no_adapter_exists(
    db_session, override_get_db, monkeypatch
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    monkeypatch.setattr(
        "app.services.narrative_providers.factory.get_settings",
        lambda: Settings(narrative_provider="llm", llm_api_key="sk-fake", llm_model="gpt-4"),
    )

    response = _generate(created["id"], token)

    assert response.status_code == 503
    assert response.json()["detail"] == "설명문 생성 서비스를 사용할 수 없습니다."
    assert "sk-fake" not in response.text


def test_llm_provider_error_never_falls_back_to_mock(db_session, override_get_db, monkeypatch):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    monkeypatch.setattr(
        "app.services.narrative_providers.factory.get_settings",
        lambda: Settings(narrative_provider="llm", llm_api_key=None, llm_model=""),
    )

    response = _generate(created["id"], token)

    assert response.status_code == 503  # 200(Mock 성공)으로 조용히 대체되지 않는다.


# ============================== 검증 실패 경로 =================================


def test_a_provider_result_that_fails_validation_writes_nothing(
    db_session, override_get_db, monkeypatch
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    fake_provider = _FakeProvider(result=_invalid_llm_result_with_banned_phrase())
    monkeypatch.setattr(
        "app.routers.clinical_reports.get_narrative_provider", lambda: fake_provider
    )
    ai_summary_count_before = db_session.query(AiSummary).count()
    audit_log_count_before = db_session.query(AuditLog).count()

    response = _generate(created["id"], token)

    assert response.status_code == 502
    assert response.json()["detail"] == "생성된 설명문이 검증을 통과하지 못했습니다."
    assert "banned_phrase_detected" not in response.text
    assert fake_provider.called is True
    assert db_session.query(AiSummary).count() == ai_summary_count_before
    assert db_session.query(AuditLog).count() == audit_log_count_before
    report = db_session.query(ClinicalReport).filter_by(id=created["id"]).first()
    assert report.content["narrative"] is None


# ============================== 성공 경로(가짜 provider) =======================


def test_a_valid_llm_result_is_saved_with_the_llm_audit_reason(
    db_session, override_get_db, monkeypatch
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    fake_provider = _FakeProvider(result=VALID_LLM_RESULT)
    monkeypatch.setattr(
        "app.routers.clinical_reports.get_narrative_provider", lambda: fake_provider
    )

    response = _generate(created["id"], token)

    assert response.status_code == 200
    body = response.json()
    assert body["content"]["narrative"] == "HbA1c 결과가 확인됩니다."

    audit_log = (
        db_session.query(AuditLog)
        .filter_by(action="GENERATE_REPORT_NARRATIVE", resource_id=str(created["id"]))
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_log.reason == "llm_generated_narrative"
    assert "test-model" not in audit_log.reason
    assert "LLM" not in audit_log.reason


# ============================== 기존 narrative가 있으면 provider 미호출 =========


def test_provider_is_never_called_when_narrative_already_exists(
    db_session, override_get_db, monkeypatch
):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)
    _generate(created["id"], token)  # 기본 mock provider로 narrative를 먼저 채운다.

    def _fail_if_called():
        raise AssertionError("narrative가 이미 있으면 provider를 호출하면 안 된다")

    monkeypatch.setattr("app.routers.clinical_reports.get_narrative_provider", _fail_if_called)

    response = _generate(created["id"], token)

    assert response.status_code == 200


# ============================== mock 기본값 무변경(회귀 고정핀) ================


def test_mock_default_still_succeeds_exactly_like_task_16(db_session, override_get_db):
    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _generate(created["id"], token)

    assert response.status_code == 200
    body = response.json()
    assert body["content"]["narrative"] is not None

    audit_log = (
        db_session.query(AuditLog)
        .filter_by(action="GENERATE_REPORT_NARRATIVE", resource_id=str(created["id"]))
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_log.reason == "deterministic_mock_narrative"


# ============================== Task C2: ambient 환경변수 무관 ==================


def test_ambient_llm_environment_variables_have_no_effect_on_this_test(
    db_session, override_get_db, monkeypatch
):
    # 실제 backend/.env 파일은 건드리지 않는다 - OS 환경변수만으로 llm/
    # ollama 환경을 흉내 낸다. _default_to_mock_settings 오토유즈
    # 픽스처가 factory.get_settings 자체를 대체하므로, 이 환경변수는
    # 전혀 읽히지 않고 실제 Ollama/네트워크 호출도 발생하지 않아야 한다.
    monkeypatch.setenv("NARRATIVE_PROVIDER", "llm")
    monkeypatch.setenv("LLM_VENDOR", "ollama")
    monkeypatch.setenv("LLM_MODEL", "qwen3:8b")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434")

    seed(db_session)
    patient = _endo_patient(db_session)
    token = _login(ENDOCRINE_DOCTOR_EMAIL)
    encounter_id = _first_encounter_id(db_session, patient.id)
    created = _create_report(token, patient.id, encounter_id)

    response = _generate(created["id"], token)

    assert response.status_code == 200
    audit_log = (
        db_session.query(AuditLog)
        .filter_by(action="GENERATE_REPORT_NARRATIVE", resource_id=str(created["id"]))
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit_log.reason == "deterministic_mock_narrative"
