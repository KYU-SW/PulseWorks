"""HL7-4A: CDA Intermediate Representation 최소 모델 테스트.

Identifier/CodedValue/PhysicalQuantity/TimePoint/TimeInterval은 전부
immutable(frozen dataclass)이며, XML 태그/네임스페이스 문자열을 전혀
모른다(Exporter만 안다) — app/services/cda/models.py 자체 docstring 참고.
"""

import pytest

from app.services.cda.models import (
    CodedValue,
    Identifier,
    PhysicalQuantity,
    TimeInterval,
    TimePoint,
)


class TestIdentifier:
    def test_valid_root_and_extension(self):
        identifier = Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427", extension="SYN-0001")
        assert identifier.root == "1b4e28ba-2fa1-11d2-883f-0016d3cca427"
        assert identifier.extension == "SYN-0001"

    def test_root_without_extension_is_allowed(self):
        identifier = Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427")
        assert identifier.extension is None

    def test_rejects_urn_uuid_prefix(self):
        with pytest.raises(ValueError, match="urn:uuid:"):
            Identifier(root="urn:uuid:1b4e28ba-2fa1-11d2-883f-0016d3cca427")

    def test_rejects_malformed_uuid_syntax(self):
        with pytest.raises(ValueError, match="UUID"):
            Identifier(root="not-a-uuid")

    def test_rejects_leading_whitespace(self):
        with pytest.raises(ValueError, match="whitespace"):
            Identifier(root=" 1b4e28ba-2fa1-11d2-883f-0016d3cca427")

    def test_rejects_trailing_whitespace(self):
        with pytest.raises(ValueError, match="whitespace"):
            Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427 ")

    def test_rejects_empty_root(self):
        with pytest.raises(ValueError, match="root"):
            Identifier(root="")

    def test_rejects_empty_string_extension(self):
        # extension은 None(없음) 또는 비어있지 않은 문자열만 허용한다 -
        # ""는 "없음"과 "빈 문자열"을 모호하게 만들어 금지한다(HL7-3 §6).
        with pytest.raises(ValueError, match="extension"):
            Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427", extension="")

    def test_does_not_restrict_uuid_version(self):
        # HL7-3 §5 결정: CDA schema가 UUID version을 검사하지 않으므로
        # 애플리케이션도 추가 제약을 걸지 않는다. 버전 니블이 1인 UUID도
        # 그대로 허용되어야 한다.
        identifier = Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427")
        assert identifier.root.split("-")[2].startswith("1")

    def test_same_source_and_config_yields_equal_identifier(self):
        a = Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427", extension="SYN-0001")
        b = Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427", extension="SYN-0001")
        assert a == b


class TestCodedValue:
    def test_known_state_requires_code_and_code_system(self):
        value = CodedValue.known(code="8480-6", code_system="2.16.840.1.113883.6.1", display_name="Systolic")
        assert value.state == "known"
        assert value.code == "8480-6"
        assert value.code_system == "2.16.840.1.113883.6.1"

    def test_unknown_state_carries_null_flavor_and_original_text(self):
        value = CodedValue.unknown(original_text="HbA1c")
        assert value.state == "unknown"
        assert value.null_flavor == "UNK"
        assert value.original_text == "HbA1c"
        # unknown 상태는 raw_code/code를 갖지 않는다 - "값 자체가 없음"과
        # "값은 있지만 체계가 불명확함"을 구조적으로 구분한다(HL7-2 §9).
        assert value.code is None
        assert value.raw_code is None

    def test_raw_unverified_state_preserves_raw_code_without_code_system(self):
        value = CodedValue.raw_unverified(raw_code="E11.9", original_text="2형 당뇨병")
        assert value.state == "raw_unverified"
        assert value.raw_code == "E11.9"
        assert value.original_text == "2형 당뇨병"
        # raw_unverified는 codeSystem을 추측하지 않는다 - KCD/ICD-10/SNOMED
        # 어느 것도 아니라는 사실 자체를 타입으로 강제한다.
        assert value.code_system is None

    def test_states_are_mutually_exclusive_constructors(self):
        known = CodedValue.known(code="X", code_system="Y")
        assert known.null_flavor is None
        assert known.raw_code is None


class TestPhysicalQuantity:
    def test_holds_value_and_unit(self):
        pq = PhysicalQuantity(value="120", unit="mm[Hg]")
        assert pq.value == "120"
        assert pq.unit == "mm[Hg]"


class TestTimePointAndInterval:
    def test_time_point_requires_timezone_aware_datetime(self):
        import datetime

        with pytest.raises(ValueError, match="timezone"):
            TimePoint(value=datetime.datetime(2026, 3, 10, 9, 0, 0))

    def test_time_interval_allows_open_ended_high(self):
        import datetime

        low = TimePoint(value=datetime.datetime(2026, 3, 10, 9, 0, 0, tzinfo=datetime.timezone.utc))
        interval = TimeInterval(low=low, high=None)
        assert interval.high is None


class TestCdaObservationAndOrganizer:
    def test_observation_holds_identifier_code_and_value(self):
        from app.services.cda.models import CdaObservation

        obs = CdaObservation(
            identifier=Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427", extension="vital_sign:1"),
            code=CodedValue.known(code="8310-5", code_system="2.16.840.1.113883.6.1"),
            value=PhysicalQuantity(value="36.5", unit="Cel"),
            effective_time=TimePoint(
                value=__import__("datetime").datetime(2026, 3, 10, 9, 0, tzinfo=__import__("datetime").timezone.utc)
            ),
        )
        assert obs.code.code == "8310-5"
        assert obs.value.unit == "Cel"

    def test_organizer_requires_exactly_two_or_zero_components(self):
        from app.services.cda.models import CdaObservation, CdaOrganizer

        import datetime

        ts = TimePoint(value=datetime.datetime(2026, 3, 10, 9, 0, tzinfo=datetime.timezone.utc))
        systolic = CdaObservation(
            identifier=Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427", extension="vital_sign:1:systolic"),
            code=CodedValue.known(code="8480-6", code_system="2.16.840.1.113883.6.1"),
            value=PhysicalQuantity(value="120", unit="mm[Hg]"),
            effective_time=ts,
        )
        diastolic = CdaObservation(
            identifier=Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427", extension="vital_sign:1:diastolic"),
            code=CodedValue.known(code="8462-4", code_system="2.16.840.1.113883.6.1"),
            value=PhysicalQuantity(value="80", unit="mm[Hg]"),
            effective_time=ts,
        )

        status = CodedValue.known(code="completed", code_system="2.16.840.1.113883.5.14")
        organizer = CdaOrganizer(
            identifier=Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427", extension="vital_sign:1"),
            code=CodedValue.known(code="85354-9", code_system="2.16.840.1.113883.6.1"),
            components=(systolic, diastolic),
            status=status,
        )
        assert len(organizer.components) == 2

        with pytest.raises(ValueError, match="2개"):
            CdaOrganizer(
                identifier=Identifier(root="1b4e28ba-2fa1-11d2-883f-0016d3cca427", extension="vital_sign:2"),
                code=CodedValue.known(code="85354-9", code_system="2.16.840.1.113883.6.1"),
                components=(systolic,),
                status=status,
            )
