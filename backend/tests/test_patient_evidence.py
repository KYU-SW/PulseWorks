from app.schemas.clinical_report import EmrSnapshot
from app.services.patient_evidence import build_patient_evidence


def _snapshot(**overrides) -> EmrSnapshot:
    base = {
        "patient": {"id": 1, "mrn": "SYN-0001", "name": "합성환자-내분비01", "birth_date": "1968-04-12"},
        "encounters": [
            {
                "id": 1, "department": "ENDOCRINOLOGY", "encounter_type": "OUTPATIENT",
                "start_time": "2026-03-10T09:00:00Z", "end_time": None,
            }
        ],
        "diagnoses": [],
        "lab_results": [],
        "lab_trends": [],
        "prescriptions": [],
        "allergies": [],
        "safety_alerts": [],
        "clinical_notes": [],
        "vital_signs": [],
        "source_record_ids": ["encounter:1"],
    }
    base.update(overrides)
    return EmrSnapshot.model_validate(base)


def _vital(id_: int, vital_type: str = "BLOOD_PRESSURE", value: str = "120", value_secondary: str | None = "80"):
    return {
        "id": id_, "encounter_id": 1, "vital_type": vital_type,
        "value": value, "value_secondary": value_secondary, "unit": "mmHg",
        "measured_at": "2026-03-10T09:00:00Z",
    }


# Task F4-B: patient_evidence.py에 vital_sign 분기 추가.


def test_vital_sign_produces_an_evidence_sentence():
    snapshot = _snapshot(
        vital_signs=[_vital(10)],
        source_record_ids=["encounter:1", "vital_sign:10"],
    )

    labels = build_patient_evidence(snapshot)

    assert any("활력징후" in label for label in labels)


def test_vital_sign_sentence_includes_date_and_department():
    snapshot = _snapshot(
        vital_signs=[_vital(10)],
        source_record_ids=["encounter:1", "vital_sign:10"],
    )

    labels = build_patient_evidence(snapshot)

    assert "2026년 3월 10일 내분비내과 활력징후 측정" in labels


def test_multiple_vital_signs_in_the_same_encounter_produce_one_deduped_sentence():
    snapshot = _snapshot(
        vital_signs=[
            _vital(10, "BLOOD_PRESSURE", "120", "80"),
            _vital(11, "BODY_TEMPERATURE", "36.5", None),
            _vital(12, "HEART_RATE", "72", None),
        ],
        source_record_ids=["encounter:1", "vital_sign:10", "vital_sign:11", "vital_sign:12"],
    )

    labels = build_patient_evidence(snapshot)

    vital_sign_labels = [label for label in labels if "활력징후" in label]
    assert len(vital_sign_labels) == 1


def test_vital_sign_sentence_never_leaks_internal_id_or_vital_type():
    snapshot = _snapshot(
        vital_signs=[_vital(999)],
        source_record_ids=["encounter:1", "vital_sign:999"],
    )

    labels = build_patient_evidence(snapshot)

    joined = " ".join(labels)
    assert "999" not in joined
    assert "BLOOD_PRESSURE" not in joined
    assert "vital_sign" not in joined


def test_vital_sign_with_no_matching_encounter_is_skipped_quietly():
    # source_record_ids에는 있지만 vital_signs 목록에 해당 id가 없는
    # (정상적으로는 일어나지 않는) 상황 - 조용히 건너뛴다.
    snapshot = _snapshot(source_record_ids=["encounter:1", "vital_sign:9999"])

    labels = build_patient_evidence(snapshot)

    assert not any("999" in label for label in labels)
