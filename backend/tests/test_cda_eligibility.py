"""HL7-4A §25: Export Eligibility policy TDD.

이번 작업에서는 실제 API endpoint를 만들지 않는다 - authorization은
이 policy에 넣지 않는다(API 계층 책임, HL7-2 §4/§24).
"""

import pytest

from app.services.cda.eligibility import check_cda_export_eligibility
from app.services.cda.errors import CdaEligibilityError


def _eligible_kwargs(**overrides):
    base = dict(
        status="APPROVED",
        report_type="DOCTOR_REFERENCE",
        scope_type="SINGLE_ENCOUNTER",
        encounter_id=10,
        content_available=True,
        snapshot_parseable=True,
    )
    base.update(overrides)
    return base


class TestCdaExportEligibility:
    def test_approved_doctor_reference_single_encounter_is_allowed(self):
        check_cda_export_eligibility(**_eligible_kwargs())  # raises 없이 통과

    def test_draft_is_rejected(self):
        with pytest.raises(CdaEligibilityError) as exc_info:
            check_cda_export_eligibility(**_eligible_kwargs(status="DRAFT"))
        assert exc_info.value.code == "NOT_APPROVED"

    def test_rejected_is_rejected(self):
        with pytest.raises(CdaEligibilityError) as exc_info:
            check_cda_export_eligibility(**_eligible_kwargs(status="REJECTED"))
        assert exc_info.value.code == "NOT_APPROVED"

    def test_wrong_report_type_is_rejected(self):
        with pytest.raises(CdaEligibilityError) as exc_info:
            check_cda_export_eligibility(**_eligible_kwargs(report_type="HANDOFF"))
        assert exc_info.value.code == "UNSUPPORTED_REPORT_TYPE"

    def test_wrong_scope_type_is_rejected(self):
        with pytest.raises(CdaEligibilityError) as exc_info:
            check_cda_export_eligibility(**_eligible_kwargs(scope_type="PERIOD"))
        assert exc_info.value.code == "UNSUPPORTED_SCOPE"

    def test_missing_encounter_id_is_rejected(self):
        with pytest.raises(CdaEligibilityError) as exc_info:
            check_cda_export_eligibility(**_eligible_kwargs(encounter_id=None))
        assert exc_info.value.code == "MISSING_SNAPSHOT"

    def test_missing_content_is_rejected(self):
        with pytest.raises(CdaEligibilityError) as exc_info:
            check_cda_export_eligibility(**_eligible_kwargs(content_available=False))
        assert exc_info.value.code == "MISSING_SNAPSHOT"

    def test_unparseable_snapshot_is_rejected(self):
        with pytest.raises(CdaEligibilityError) as exc_info:
            check_cda_export_eligibility(**_eligible_kwargs(snapshot_parseable=False))
        assert exc_info.value.code == "MISSING_SNAPSHOT"
