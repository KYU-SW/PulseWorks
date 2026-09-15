"""합성(가짜) 교육용 데이터 시더.

이 스크립트가 만드는 모든 User/Patient/임상 레코드는 100% 합성 데이터다.
실제 환자, 실제 의료진, 실제 의료기관의 정보를 담지 않는다.

- Patient.mrn: 전부 "SYN-" 접두사
- User.email: 전부 "@example.test" 도메인(IANA가 테스트용으로 예약한 TLD)
- Patient/User.full_name: 전부 "합성"이 포함된 placeholder 이름
- Diagnosis.description / ClinicalNote.note_text: 필요한 경우 "(합성 데이터)" 표시
- 주민등록번호 등 실제 개인식별번호 필드는 아예 만들지 않는다.

Task 4(합성 데이터 Seed)는 인증/로그인을 구현하지 않았기 때문에, 처음 만들어질
때는 User.hashed_password에 그 자체로 인증에 쓰일 수 없는 placeholder 문자열이
들어갔다. Task 5(인증)부터는 이 스크립트가 실제 bcrypt 해시로 교체한다 —
아래 DEMO_PASSWORD는 로컬 테스트/시연 전용 합성 계정 비밀번호이며, 실제 운영
자격증명이 아니다. Seed를 다시 실행하면 이미 존재하는 계정도 placeholder가
남아있는 경우에만 해시가 갱신되고, 다른 임상 데이터는 중복 생성되지 않는다.
"""

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Allergy,
    AssignmentRole,
    ClinicalNote,
    Department,
    Diagnosis,
    Encounter,
    EncounterType,
    LabResult,
    Order,
    Patient,
    PatientAssignment,
    Prescription,
    Role,
    SourceType,
    User,
)

# Not a real password hash — Task 5 replaces this with a real bcrypt hash of
# DEMO_PASSWORD for every synthetic account. Kept only as the sentinel value
# _get_or_create_user checks for to decide whether an existing row's
# password still needs healing.
PLACEHOLDER_HASHED_PASSWORD = "SEED_PLACEHOLDER_NOT_A_REAL_HASH__SEE_AUTH_TASK"

# Local demo/test password for every synthetic account this script creates.
# This is NOT a real credential — it only ever protects synthetic accounts
# in a local/CI database and must never be reused for anything real. Also
# documented in README.md's local demo accounts section.
DEMO_PASSWORD = "demo1234"


def _is_abnormal(value: float, reference_low: float, reference_high: float) -> bool:
    """검사값이 참고범위를 벗어나는지 판단하는 순수 함수.

    이후 규칙 엔진 Task에서 app.services.safety_rules로 승격될 수 있는 로직이지만,
    이 Task는 그 모듈을 만들지 않으므로 seed 전용 로컬 헬퍼로 둔다.
    """
    return value < reference_low or value > reference_high


def _get_or_create_user(db: Session, email: str, **fields) -> tuple[User, bool]:
    user = db.query(User).filter_by(email=email).first()
    if user is not None:
        # Heal accounts created before Task 5 existed (still carrying
        # Task 4's non-functional placeholder) without touching anything
        # else about the row, and without creating a new row.
        if user.hashed_password == PLACEHOLDER_HASHED_PASSWORD:
            user.hashed_password = hash_password(DEMO_PASSWORD)
        return user, False
    user = User(email=email, hashed_password=hash_password(DEMO_PASSWORD), **fields)
    db.add(user)
    db.flush()
    return user, True


def _get_or_create_patient(db: Session, mrn: str, **fields) -> tuple[Patient, bool]:
    patient = db.query(Patient).filter_by(mrn=mrn).first()
    if patient is not None:
        return patient, False
    patient = Patient(mrn=mrn, **fields)
    db.add(patient)
    db.flush()
    return patient, True


def _utc(*args) -> datetime:
    return datetime(*args, tzinfo=timezone.utc)


def seed(db: Session) -> None:
    # ------------------------------------------------------------------
    # 1. 합성 사용자 계정 (직종별 최소 1명 + PATIENT 역할 최소 2명)
    # ------------------------------------------------------------------
    endocrine_doctor, _ = _get_or_create_user(
        db, "endocrine.doctor@example.test",
        full_name="합성의사-내분비01", role=Role.DOCTOR, department=Department.ENDOCRINOLOGY,
    )
    orthopedic_doctor, _ = _get_or_create_user(
        db, "orthopedic.doctor@example.test",
        full_name="합성의사-정형외과01", role=Role.DOCTOR, department=Department.ORTHOPEDICS,
    )
    emergency_doctor, _ = _get_or_create_user(
        db, "emergency.doctor@example.test",
        full_name="합성의사-응급01", role=Role.DOCTOR, department=Department.EMERGENCY_MEDICINE,
    )
    nurse1, _ = _get_or_create_user(
        db, "nurse1@example.test",
        full_name="합성간호사01", role=Role.NURSE, department=Department.ENDOCRINOLOGY,
    )
    _get_or_create_user(
        db, "admin.staff@example.test",
        full_name="합성원무01", role=Role.ADMIN_STAFF,
    )
    _get_or_create_user(
        db, "system.admin@example.test",
        full_name="합성관리자01", role=Role.SYSTEM_ADMIN,
    )

    department_doctors = [endocrine_doctor, orthopedic_doctor, emergency_doctor]

    # ------------------------------------------------------------------
    # 2. 핵심 환자 A: 내분비내과 — 3회 방문, 상승하는 HbA1c 시계열
    # ------------------------------------------------------------------
    endo_patient, endo_created = _get_or_create_patient(
        db, "SYN-0001",
        full_name="합성환자-내분비01", birth_date=date(1968, 4, 12), sex="F",
    )
    # Outside the `if endo_created:` gate on purpose: this must run on every
    # seed() call (not just when the Patient row is brand new) so that a
    # rerun still heals patient1's password if it's still the Task 4
    # placeholder — get_or_create_user's own existence check makes this a
    # no-op (no duplicate row) when patient1 already has a real hash.
    _get_or_create_user(
        db, "patient1@example.test",
        full_name=endo_patient.full_name, role=Role.PATIENT, patient_id=endo_patient.id,
    )

    if endo_created:
        db.add(
            PatientAssignment(
                patient_id=endo_patient.id,
                staff_user_id=endocrine_doctor.id,
                department=Department.ENDOCRINOLOGY,
                assignment_role=AssignmentRole.ATTENDING_PHYSICIAN,
                created_at=_utc(2026, 1, 1, 9, 0),
            )
        )
        db.add(
            PatientAssignment(
                patient_id=endo_patient.id,
                staff_user_id=nurse1.id,
                department=Department.ENDOCRINOLOGY,
                assignment_role=AssignmentRole.PRIMARY_NURSE,
                created_at=_utc(2026, 1, 1, 9, 0),
            )
        )

        db.add(
            Allergy(
                patient_id=endo_patient.id,
                substance="Penicillin",
                reaction="두드러기 (합성 데이터)",
                severity="MODERATE",
                recorded_at=_utc(2026, 1, 1, 9, 0),
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )

        visits = [
            {
                "start": _utc(2026, 3, 10, 9, 0),
                "hba1c": 7.2,
                "glucose": 130,
                "diagnosis": "2형 당뇨병 신규 진단 (합성 데이터)",
                "note": "합성 데이터: 내분비내과 초진. 공복혈당 및 HbA1c 상승 확인, 생활습관 교육 시행.",
                "medication": ("Metformin", "500mg"),
            },
            {
                "start": _utc(2026, 6, 10, 9, 0),
                "hba1c": 7.8,
                "glucose": 145,
                "diagnosis": "2형 당뇨병, 경과 관찰 (합성 데이터)",
                "note": "합성 데이터: 3개월 추적 방문. HbA1c 소폭 상승, 약물 순응도 재교육 및 용량 조정.",
                "medication": ("Metformin", "1000mg"),
            },
            {
                "start": _utc(2026, 9, 5, 9, 0),
                "hba1c": 8.1,
                "glucose": 160,
                "diagnosis": "2형 당뇨병, 경과 관찰 (합성 데이터)",
                "note": "합성 데이터: 6개월 추적 방문. 혈당 조절 불충분, 급성 인후염 동반으로 항생제 처방.",
                "medication": ("Penicillin V", "500mg"),
            },
        ]

        last_encounter = None
        for visit in visits:
            encounter = Encounter(
                patient_id=endo_patient.id,
                department=Department.ENDOCRINOLOGY,
                encounter_type=EncounterType.OUTPATIENT,
                start_time=visit["start"],
                created_by_user_id=endocrine_doctor.id,
            )
            db.add(encounter)
            db.flush()
            last_encounter = encounter

            db.add(
                Diagnosis(
                    encounter_id=encounter.id,
                    code="E11.9",
                    description=visit["diagnosis"],
                    diagnosed_at=visit["start"],
                    source_type=SourceType.INSTITUTION_GENERATED,
                )
            )

            hba1c_order = Order(
                encounter_id=encounter.id,
                test_name="HbA1c",
                ordered_at=visit["start"],
                source_type=SourceType.INSTITUTION_GENERATED,
            )
            glucose_order = Order(
                encounter_id=encounter.id,
                test_name="Fasting Glucose",
                ordered_at=visit["start"],
                source_type=SourceType.INSTITUTION_GENERATED,
            )
            db.add_all([hba1c_order, glucose_order])
            db.flush()

            db.add(
                LabResult(
                    encounter_id=encounter.id,
                    order_id=hba1c_order.id,
                    test_name="HbA1c",
                    value=visit["hba1c"],
                    unit="%",
                    reference_low=4.0,
                    reference_high=6.0,
                    is_abnormal=_is_abnormal(visit["hba1c"], 4.0, 6.0),
                    measured_at=visit["start"],
                    source_type=SourceType.INSTITUTION_GENERATED,
                )
            )
            db.add(
                LabResult(
                    encounter_id=encounter.id,
                    order_id=glucose_order.id,
                    test_name="Fasting Glucose",
                    value=visit["glucose"],
                    unit="mg/dL",
                    reference_low=70.0,
                    reference_high=100.0,
                    is_abnormal=_is_abnormal(visit["glucose"], 70.0, 100.0),
                    measured_at=visit["start"],
                    source_type=SourceType.INSTITUTION_GENERATED,
                )
            )

            medication_name, dosage = visit["medication"]
            db.add(
                Prescription(
                    encounter_id=encounter.id,
                    medication_name=medication_name,
                    dosage=dosage,
                    prescribed_by_user_id=endocrine_doctor.id,
                    prescribed_at=visit["start"],
                    source_type=SourceType.INSTITUTION_GENERATED,
                )
            )

            db.add(
                ClinicalNote(
                    encounter_id=encounter.id,
                    author_user_id=endocrine_doctor.id,
                    note_text=visit["note"],
                    created_at=visit["start"],
                    source_type=SourceType.INSTITUTION_GENERATED,
                )
            )

        # 환자가 방문 사이(2026-07-20)에 집에서 직접 측정해 입력한 자가측정
        # 혈당값. LabResult.encounter_id는 NOT NULL이므로 실제로는 다음
        # 방문(3차, 2026-09-05)에서 의료진에게 보고·기록된 값으로 그 Encounter에
        # 연결한다 — institution Order는 없으므로 order_id=None, 측정 시각
        # (measured_at)은 실제 측정된 시점을 그대로 기록한다.
        db.add(
            LabResult(
                encounter_id=last_encounter.id,
                order_id=None,
                test_name="자가측정 혈당 (합성 데이터, 환자 입력)",
                value=180.0,
                unit="mg/dL",
                reference_low=70.0,
                reference_high=140.0,
                is_abnormal=_is_abnormal(180.0, 70.0, 140.0),
                measured_at=_utc(2026, 7, 20, 21, 0),
                source_type=SourceType.PATIENT_REPORTED,
            )
        )

    db.flush()

    # ------------------------------------------------------------------
    # 3. 핵심 환자 B: 정형외과 — 통증 + 영상검사 요청/보고(Order+ClinicalNote)
    # ------------------------------------------------------------------
    ortho_patient, ortho_created = _get_or_create_patient(
        db, "SYN-0002",
        full_name="합성환자-정형외과01", birth_date=date(1980, 11, 3), sex="M",
    )
    # Same reasoning as patient1 above: must run every time, not only when
    # the Patient row is new, so a rerun heals patient2's password too.
    _get_or_create_user(
        db, "patient2@example.test",
        full_name=ortho_patient.full_name, role=Role.PATIENT, patient_id=ortho_patient.id,
    )

    if ortho_created:
        db.add(
            PatientAssignment(
                patient_id=ortho_patient.id,
                staff_user_id=orthopedic_doctor.id,
                department=Department.ORTHOPEDICS,
                assignment_role=AssignmentRole.ATTENDING_PHYSICIAN,
                created_at=_utc(2026, 8, 1, 10, 0),
            )
        )

        encounter = Encounter(
            patient_id=ortho_patient.id,
            department=Department.ORTHOPEDICS,
            encounter_type=EncounterType.OUTPATIENT,
            start_time=_utc(2026, 8, 1, 10, 0),
            created_by_user_id=orthopedic_doctor.id,
        )
        db.add(encounter)
        db.flush()

        db.add(
            Diagnosis(
                encounter_id=encounter.id,
                code="M17.9",
                description="좌측 무릎 골관절염 의심 (합성 데이터)",
                diagnosed_at=encounter.start_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )
        # 영상검사 "요청"은 Order로 표현 (새 Imaging 모델을 만들지 않음).
        db.add(
            Order(
                encounter_id=encounter.id,
                test_name="좌측 무릎 X-ray",
                ordered_at=encounter.start_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )
        # 영상검사 "보고(판독 소견)"는 수치 스키마인 LabResult에 맞지 않아
        # ClinicalNote로 표현 (역시 새 모델을 만들지 않음).
        db.add(
            ClinicalNote(
                encounter_id=encounter.id,
                author_user_id=orthopedic_doctor.id,
                note_text=(
                    "합성 데이터: 영상검사 보고 — 좌측 무릎 X-ray 판독 소견: "
                    "경미한 퇴행성 관절 변화, 급성 골절 소견 없음."
                ),
                created_at=encounter.start_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )
        db.add(
            ClinicalNote(
                encounter_id=encounter.id,
                author_user_id=orthopedic_doctor.id,
                note_text="합성 데이터: 좌측 무릎 통증 8주 지속, 계단 오르내릴 때 악화. 압통 및 경미한 부종 관찰.",
                created_at=encounter.start_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )
        db.add(
            Prescription(
                encounter_id=encounter.id,
                medication_name="Ibuprofen",
                dosage="400mg",
                prescribed_by_user_id=orthopedic_doctor.id,
                prescribed_at=encounter.start_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )

    db.flush()

    # ------------------------------------------------------------------
    # 4. 핵심 환자 C: 응급의학과 — 응급 방문, 활력징후/우선확인 검사
    # ------------------------------------------------------------------
    emergency_patient, emergency_created = _get_or_create_patient(
        db, "SYN-0003",
        full_name="합성환자-응급01", birth_date=date(1990, 2, 20), sex="M",
    )

    if emergency_created:
        db.add(
            PatientAssignment(
                patient_id=emergency_patient.id,
                staff_user_id=emergency_doctor.id,
                department=Department.EMERGENCY_MEDICINE,
                assignment_role=AssignmentRole.ATTENDING_PHYSICIAN,
                created_at=_utc(2026, 9, 10, 22, 0),
            )
        )

        encounter = Encounter(
            patient_id=emergency_patient.id,
            department=Department.EMERGENCY_MEDICINE,
            encounter_type=EncounterType.EMERGENCY,
            start_time=_utc(2026, 9, 10, 22, 0),
            created_by_user_id=emergency_doctor.id,
        )
        db.add(encounter)
        db.flush()

        db.add(
            Diagnosis(
                encounter_id=encounter.id,
                code="R07.9",
                description="흉통, 원인 감별 중 (합성 데이터)",
                diagnosed_at=encounter.start_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )

        # 활력징후에 해당하는 측정값 (전용 Vitals 모델 없이 LabResult로 표현).
        db.add(
            LabResult(
                encounter_id=encounter.id,
                order_id=None,
                test_name="Heart Rate",
                value=118.0,
                unit="bpm",
                reference_low=60.0,
                reference_high=100.0,
                is_abnormal=_is_abnormal(118.0, 60.0, 100.0),
                measured_at=encounter.start_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )
        # 우선 확인이 필요한 응급 검사(예: 심장효소) — 참고범위를 크게 벗어남.
        troponin_order = Order(
            encounter_id=encounter.id,
            test_name="Troponin",
            ordered_at=encounter.start_time,
            source_type=SourceType.INSTITUTION_GENERATED,
        )
        db.add(troponin_order)
        db.flush()
        db.add(
            LabResult(
                encounter_id=encounter.id,
                order_id=troponin_order.id,
                test_name="Troponin",
                value=0.8,
                unit="ng/mL",
                reference_low=0.0,
                reference_high=0.04,
                is_abnormal=_is_abnormal(0.8, 0.0, 0.04),
                measured_at=encounter.start_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )

        db.add(
            ClinicalNote(
                encounter_id=encounter.id,
                author_user_id=emergency_doctor.id,
                note_text=(
                    "합성 데이터: 응급실 초진 기록 — 급성 흉통으로 내원, 활력징후 불안정 및 "
                    "Troponin 상승 확인, 심장내과 협진 및 추가 검사 진행 중."
                ),
                created_at=encounter.start_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )

    db.flush()

    # ------------------------------------------------------------------
    # 5. 나머지 합성 환자 (최소 10명 요건을 채우는 일반 환자 7명)
    #    각각 담당의 1명 + 그 진료과에 맞는 간단한 Encounter/Diagnosis만 부여.
    # ------------------------------------------------------------------
    filler_specs = [
        ("SYN-0004", "합성환자-일반01", date(1975, 5, 1), "F"),
        ("SYN-0005", "합성환자-일반02", date(1982, 9, 14), "M"),
        ("SYN-0006", "합성환자-일반03", date(1960, 12, 30), "F"),
        ("SYN-0007", "합성환자-일반04", date(1995, 3, 22), "M"),
        ("SYN-0008", "합성환자-일반05", date(1988, 7, 7), "F"),
        ("SYN-0009", "합성환자-일반06", date(1970, 1, 18), "M"),
        ("SYN-0010", "합성환자-일반07", date(2001, 6, 9), "F"),
    ]

    department_by_doctor = {
        endocrine_doctor.id: Department.ENDOCRINOLOGY,
        orthopedic_doctor.id: Department.ORTHOPEDICS,
        emergency_doctor.id: Department.EMERGENCY_MEDICINE,
    }

    for i, (mrn, name, birth_date, sex) in enumerate(filler_specs):
        patient, created = _get_or_create_patient(
            db, mrn, full_name=name, birth_date=birth_date, sex=sex
        )
        if not created:
            continue

        doctor = department_doctors[i % len(department_doctors)]
        department = department_by_doctor[doctor.id]
        visit_time = _utc(2026, 2, 1, 9, 0)

        db.add(
            PatientAssignment(
                patient_id=patient.id,
                staff_user_id=doctor.id,
                department=department,
                assignment_role=AssignmentRole.ATTENDING_PHYSICIAN,
                created_at=visit_time,
            )
        )

        encounter = Encounter(
            patient_id=patient.id,
            department=department,
            encounter_type=EncounterType.OUTPATIENT,
            start_time=visit_time,
            created_by_user_id=doctor.id,
        )
        db.add(encounter)
        db.flush()

        db.add(
            Diagnosis(
                encounter_id=encounter.id,
                code="Z00.0",
                description="정기 건강검진, 특이 소견 없음 (합성 데이터)",
                diagnosed_at=visit_time,
                source_type=SourceType.INSTITUTION_GENERATED,
            )
        )

    db.commit()


if __name__ == "__main__":
    from app.core.db import SessionLocal

    session = SessionLocal()
    try:
        seed(session)
        # Plain ASCII only: Windows consoles often default to a non-UTF-8
        # codepage (e.g. cp949), where a Unicode em dash raises
        # UnicodeEncodeError on print() and crashes the script *after* the
        # actual seeding already committed successfully.
        print("Synthetic data seeded (idempotent - safe to re-run).")
    finally:
        session.close()
