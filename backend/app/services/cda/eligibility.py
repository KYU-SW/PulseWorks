"""HL7-4A §25: CDA Export Eligibility policy.

HL7-2 §4/§6 결정: Eligibility는 별도 policy/service 함수로 두고 router가
호출한다(API/router에서만 암묵적으로 강제하지 않음). 이 함수는 report
상태/타입/스코프/snapshot 가용성만 본다 - authorization(누가 export할
수 있는지)은 이 policy의 책임이 아니다(API 계층에서 별도로 검사).

이 파일은 HL7-2/HL7-3에서 제안한 module boundary(models/adapter/mapper/
exporter/terminology/errors)에는 없던 파일이다. §25가 "독립적인
eligibility policy/service를 구현"하도록 명시적으로 요구했고, 이
책임을 mapper.py나 errors.py에 억지로 끼워 넣는 대신 단일 책임 파일로
분리하는 것이 기존 services/ 평면 구조(authorization.py, audit.py 등
단일 목적 파일 1개=1책임) 관례와 더 일치한다고 판단해 추가했다."""

from __future__ import annotations

from app.services.cda.errors import CdaEligibilityError


def check_cda_export_eligibility(
    *,
    status: str,
    report_type: str,
    scope_type: str,
    encounter_id: int | None,
    content_available: bool,
    snapshot_parseable: bool,
) -> None:
    """조건을 만족하지 못하면 CdaEligibilityError를 던진다. 통과하면
    아무것도 반환하지 않는다(단순 게이트)."""
    if status != "APPROVED":
        raise CdaEligibilityError("NOT_APPROVED", f"report.status={status!r}는 export 대상이 아닙니다.")
    if report_type != "DOCTOR_REFERENCE":
        raise CdaEligibilityError(
            "UNSUPPORTED_REPORT_TYPE", f"report_type={report_type!r}는 이번 범위에서 지원하지 않습니다."
        )
    if scope_type != "SINGLE_ENCOUNTER":
        raise CdaEligibilityError(
            "UNSUPPORTED_SCOPE", f"scope_type={scope_type!r}는 이번 범위에서 지원하지 않습니다."
        )
    if encounter_id is None or not content_available or not snapshot_parseable:
        raise CdaEligibilityError("MISSING_SNAPSHOT", "encounter_id/content/snapshot 중 일부가 없습니다.")
