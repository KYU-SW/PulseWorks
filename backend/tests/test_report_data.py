from decimal import Decimal

import pytest

from app.models import (
    Encounter,
    Patient,
    Prescription,
    SafetyAlert,
    SafetyAlertPriority,
    SourceType,
    VitalSign,
    VitalType,
)
from app.services.report_data import ReportScopeError, collect_report_data
from app.services.safety_rules import evaluate_lab_abnormal
from scripts.seed_synthetic_data import seed


def _patient(db_session, mrn: str) -> Patient:
    return db_session.query(Patient).filter_by(mrn=mrn).first()


def _encounters(db_session, patient_id: int) -> list[Encounter]:
    return (
        db_session.query(Encounter)
        .filter_by(patient_id=patient_id)
        .order_by(Encounter.start_time)
        .all()
    )


# 1. 단일 Encounter의 환자 기본정보 수집
def test_collects_basic_patient_info(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert report.patient.id == patient.id
    assert report.patient.mrn == "SYN-0001"
    assert report.patient.name == patient.full_name
    assert report.patient.birth_date == patient.birth_date


# 2. 선택한 Encounter만 수집
def test_collects_only_the_selected_encounter(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_encounter = encounters[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert [e.id for e in report.encounters] == [first_encounter.id]


# 3. 해당 Encounter의 Diagnosis만 수집
def test_collects_only_the_selected_encounters_diagnoses(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_encounter = encounters[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert len(report.diagnoses) == 1
    assert all(d.encounter_id == first_encounter.id for d in report.diagnoses)


# 4. 해당 Encounter의 LabResult만 수집
def test_collects_only_the_selected_encounters_lab_results(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_encounter = encounters[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert {lr.test_name for lr in report.lab_results} == {"HbA1c", "Fasting Glucose"}
    assert all(lr.encounter_id == first_encounter.id for lr in report.lab_results)
    hba1c = next(lr for lr in report.lab_results if lr.test_name == "HbA1c")
    assert hba1c.value == 7.2


# 5. 해당 Encounter의 Prescription만 수집
def test_collects_only_the_selected_encounters_prescriptions(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_encounter = encounters[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert len(report.prescriptions) == 1
    assert report.prescriptions[0].medication_name == "Metformin"
    assert report.prescriptions[0].encounter_id == first_encounter.id


# 6. 해당 환자의 Allergy 전체 수집 (환자 레벨, Encounter 무관)
def test_collects_all_of_the_patients_allergies(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_encounter = encounters[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert len(report.allergies) == 1
    assert report.allergies[0].substance == "Penicillin"


# 7. 해당 Encounter의 SafetyAlert만 수집
def test_collects_only_the_selected_encounters_safety_alerts(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_encounter = encounters[0]
    other_encounter = encounters[1]
    first_prescription_id = (
        db_session.query(Prescription).filter_by(encounter_id=first_encounter.id).first().id
    )
    other_prescription_id = (
        db_session.query(Prescription).filter_by(encounter_id=other_encounter.id).first().id
    )

    alert_in_scope = SafetyAlert(
        encounter_id=first_encounter.id,
        prescription_id=first_prescription_id,
        lab_result_id=None,
        rule_id="ALLERGY_MEDICATION_CONFLICT",
        evidence={"note": "in scope"},
        priority=SafetyAlertPriority.HIGH,
        created_at=first_encounter.start_time,
    )
    alert_out_of_scope = SafetyAlert(
        encounter_id=other_encounter.id,
        prescription_id=other_prescription_id,
        lab_result_id=None,
        rule_id="ALLERGY_MEDICATION_CONFLICT",
        evidence={"note": "out of scope"},
        priority=SafetyAlertPriority.HIGH,
        created_at=other_encounter.start_time,
    )
    db_session.add_all([alert_in_scope, alert_out_of_scope])
    db_session.commit()

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert len(report.safety_alerts) == 1
    assert report.safety_alerts[0].encounter_id == first_encounter.id
    assert report.safety_alerts[0].evidence == {"note": "in scope"}


# 8. 해당 Encounter의 ClinicalNote만 수집
def test_collects_only_the_selected_encounters_clinical_notes(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_encounter = encounters[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert len(report.clinical_notes) == 1
    assert report.clinical_notes[0].encounter_id == first_encounter.id


# 9. 선택하지 않은 Encounter 데이터 미포함
def test_excludes_data_from_unselected_encounters(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_encounter = encounters[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    prescription_names = {p.medication_name for p in report.prescriptions}
    assert "Metformin" in prescription_names
    assert "Penicillin V" not in prescription_names  # 3차 방문(선택 안 함)의 처방


# 10. 다른 환자 데이터 미포함
def test_excludes_other_patients_data(db_session):
    seed(db_session)
    endo_patient = _patient(db_session, "SYN-0001")
    ortho_patient = _patient(db_session, "SYN-0002")
    first_encounter = _encounters(db_session, endo_patient.id)[0]

    report = collect_report_data(db_session, endo_patient.id, [first_encounter.id])

    all_diagnosis_text = " ".join(d.description for d in report.diagnoses)
    assert "무릎" not in all_diagnosis_text  # SYN-0002(정형외과)만의 특징적 진단
    assert report.patient.id != ortho_patient.id


# 11. 빈 encounter_ids는 범위 오류
def test_empty_encounter_ids_raises_scope_error(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")

    with pytest.raises(ReportScopeError):
        collect_report_data(db_session, patient.id, [])


# 12. 존재하지 않는 encounter_id는 범위 오류
def test_nonexistent_encounter_id_raises_scope_error(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")

    with pytest.raises(ReportScopeError):
        collect_report_data(db_session, patient.id, [999999])


# 13. 다른 환자의 encounter_id는 범위 오류 (전체 실패, 부분 반환 없음)
def test_other_patients_encounter_id_raises_scope_error(db_session):
    seed(db_session)
    endo_patient = _patient(db_session, "SYN-0001")
    ortho_patient = _patient(db_session, "SYN-0002")
    endo_first = _encounters(db_session, endo_patient.id)[0]
    ortho_first = _encounters(db_session, ortho_patient.id)[0]

    with pytest.raises(ReportScopeError):
        collect_report_data(db_session, endo_patient.id, [endo_first.id, ortho_first.id])

    # 부분 성공이 아니라 완전히 예외만 발생해야 한다 (반환값 없음은 예외로 자연히 보장됨)


# 14. 여러 encounter_ids 입력 지원
def test_supports_multiple_encounter_ids(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_two_ids = [encounters[0].id, encounters[1].id]

    report = collect_report_data(db_session, patient.id, first_two_ids)

    assert {e.id for e in report.encounters} == set(first_two_ids)
    assert len(report.diagnoses) == 2
    assert len(report.prescriptions) == 2


# 15. 임상자료가 없는 Encounter는 빈 섹션으로 정상 반환
def test_encounter_with_no_clinical_data_returns_empty_sections(db_session):
    seed(db_session)
    ortho_patient = _patient(db_session, "SYN-0002")
    ortho_encounters = _encounters(db_session, ortho_patient.id)
    # SYN-0002는 LabResult가 전혀 없다 (X-ray는 Order+ClinicalNote로 표현됨).
    target = ortho_encounters[0]

    report = collect_report_data(db_session, ortho_patient.id, [target.id])

    assert report.lab_results == []
    assert report.lab_trends == []


# 16. Task 9 검사 판정과 일치
def test_lab_result_status_matches_evaluate_lab_abnormal(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    for lr in report.lab_results:
        expected = evaluate_lab_abnormal(lr.value, lr.reference_low, lr.reference_high, lr.unit)
        assert lr.status == expected.status.value
        assert lr.rule_id == expected.rule_id


# 17. Task 11 검사명/단위 그룹화와 일치 & 18. measured_at 오름차순
def test_lab_trends_grouping_matches_task_11(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    all_encounter_ids = [e.id for e in _encounters(db_session, patient.id)]

    report = collect_report_data(db_session, patient.id, all_encounter_ids)

    test_names = [g.test_name for g in report.lab_trends]
    assert len(test_names) == len(set(test_names))
    hba1c_group = next(g for g in report.lab_trends if g.test_name == "HbA1c")
    assert [p.value for p in hba1c_group.points] == [7.2, 7.8, 8.1]
    measured_times = [p.measured_at for p in hba1c_group.points]
    assert measured_times == sorted(measured_times)


# 19. ClinicalNote 300자 제한
def test_clinical_note_preview_is_truncated_to_300_chars(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    for note in report.clinical_notes:
        assert len(note.preview_text) <= 303
        if len(note.preview_text) == 303:
            assert note.preview_text.endswith("...")


# 20. source_record_ids 형식 확인
def test_source_record_ids_format(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert f"encounter:{first_encounter.id}" in report.source_record_ids
    for record_id in report.source_record_ids:
        prefix = record_id.split(":")[0]
        # Task F4-B: VitalSign도 같은 결정적 "type:id" 형식을 공유한다.
        assert prefix in {
            "encounter", "diagnosis", "lab_result", "prescription",
            "allergy", "safety_alert", "clinical_note", "vital_sign",
        }


# 21. source_record_ids 중복 없음
def test_source_record_ids_has_no_duplicates(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    all_encounter_ids = [e.id for e in _encounters(db_session, patient.id)]

    report = collect_report_data(db_session, patient.id, all_encounter_ids)

    assert len(report.source_record_ids) == len(set(report.source_record_ids))


# 22 & 23. DB 레코드 추가·수정·삭제 없음, commit 미호출
#
# flush()는 별도로 검사하지 않는다 — SQLAlchemy는 autoflush(기본 활성화)
# 때문에 순수 조회(db.query(...).all())만 해도 세션 내부적으로 flush()를
# 호출한다. 이는 이 서비스가 명시적으로 쓰기를 요청한 것이 아니라
# SQLAlchemy 세션의 일반적인 조회 동작이며, Task 8/10/11의 다른 조회
# 라우터도 동일하게 autoflush를 거친다. 실제로 확인해야 할 것은
# "새 레코드가 실제로 생기지 않았는가"이고, 그것은 아래 개수 비교로
# 직접 검증한다.
def test_does_not_write_to_the_database(db_session, monkeypatch):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    from app.models import AuditLog

    before_prescriptions = db_session.query(Prescription).count()
    before_audit_logs = db_session.query(AuditLog).count()
    before_safety_alerts = db_session.query(SafetyAlert).count()

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("collect_report_data must never call commit()")

    monkeypatch.setattr(db_session, "commit", _fail_if_called)

    collect_report_data(db_session, patient.id, [first_encounter.id])

    assert db_session.query(Prescription).count() == before_prescriptions
    assert db_session.query(AuditLog).count() == before_audit_logs
    assert db_session.query(SafetyAlert).count() == before_safety_alerts


# 24. 동일 DB 상태와 입력에서 동일 결과
def test_same_input_returns_equivalent_result(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    first = collect_report_data(db_session, patient.id, [first_encounter.id])
    second = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert first.source_record_ids == second.source_record_ids
    assert [d.id for d in first.diagnoses] == [d.id for d in second.diagnoses]


# 25. AiSummary와 narrative 미포함
def test_report_data_has_no_narrative_or_ai_summary_fields(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    field_names = set(report.__dataclass_fields__.keys())
    assert "narrative" not in field_names
    assert "ai_summary" not in field_names
    assert "status" not in field_names
    assert "approved_by" not in field_names


# ============================== Task F4-B: VitalSign 수집 ===================
# seed()의 SYN-0001 1차 방문(2026-03-10)은 7종 VitalSign을 전부 가지고
# 있고(BMI 계산 가능 사례), 2차 방문(2026-06-10)은 혈압 역전(품질 경고)
# 사례 1건만 가지고 있다 — Task F4-A 멱등 seed 보강 참고.


def test_collects_only_the_selected_encounters_vital_signs(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert len(report.vital_signs) == 7
    assert all(v.encounter_id == first_encounter.id for v in report.vital_signs)
    assert {v.vital_type for v in report.vital_signs} == {t.value for t in VitalType}


def test_vital_signs_excludes_data_from_unselected_encounters(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    second_encounter = encounters[1]

    report = collect_report_data(db_session, patient.id, [second_encounter.id])

    assert len(report.vital_signs) == 1
    assert report.vital_signs[0].vital_type == VitalType.BLOOD_PRESSURE.value
    assert report.vital_signs[0].encounter_id == second_encounter.id


def test_vital_signs_are_sorted_by_measured_at_ascending(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    encounters = _encounters(db_session, patient.id)
    first_two_ids = [encounters[0].id, encounters[1].id]

    report = collect_report_data(db_session, patient.id, first_two_ids)

    measured_times = [v.measured_at for v in report.vital_signs]
    assert measured_times == sorted(measured_times)
    # 1차 방문(7건)이 모두 2차 방문(1건)보다 앞서야 한다.
    assert report.vital_signs[-1].encounter_id == encounters[1].id


def test_vital_signs_exclude_non_canonical_unit_records(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]
    # BODY_WEIGHT의 canonical 단위는 "kg"다 — "lb"는 비표준 단위.
    db_session.add(
        VitalSign(
            encounter_id=first_encounter.id,
            vital_type=VitalType.BODY_WEIGHT,
            value=Decimal("150.0"),
            value_secondary=None,
            unit="lb",
            measured_at=first_encounter.start_time,
            source_type=SourceType.PATIENT_REPORTED,
        )
    )
    db_session.commit()

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    assert all(v.unit != "lb" for v in report.vital_signs)
    weight_entries = [v for v in report.vital_signs if v.vital_type == VitalType.BODY_WEIGHT.value]
    assert len(weight_entries) == 1  # seed의 canonical 65.0kg만 남는다
    assert weight_entries[0].value == Decimal("65.0")


def test_vital_signs_have_no_bmi_or_quality_warning_fields(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    field_names = set(report.vital_signs[0].__dataclass_fields__.keys())
    assert "bmi" not in field_names
    assert "quality_warnings" not in field_names


def test_source_record_ids_includes_vital_sign_entries(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    vital_sign_ids = {v.id for v in report.vital_signs}
    assert vital_sign_ids  # 7건이 있어야 한다(위 테스트에서 확인됨)
    for vital_id in vital_sign_ids:
        assert f"vital_sign:{vital_id}" in report.source_record_ids


# 26. password, hashed_password, JWT, JWT_SECRET 미포함
def test_report_data_never_contains_secrets(db_session):
    seed(db_session)
    patient = _patient(db_session, "SYN-0001")
    first_encounter = _encounters(db_session, patient.id)[0]

    report = collect_report_data(db_session, patient.id, [first_encounter.id])

    dump = repr(report)
    assert "hashed_password" not in dump
    assert "password" not in dump
    assert "JWT_SECRET" not in dump
