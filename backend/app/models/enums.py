import enum


class Role(str, enum.Enum):
    DOCTOR = "DOCTOR"
    NURSE = "NURSE"
    ADMIN_STAFF = "ADMIN_STAFF"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    PATIENT = "PATIENT"


class Department(str, enum.Enum):
    ENDOCRINOLOGY = "ENDOCRINOLOGY"
    ORTHOPEDICS = "ORTHOPEDICS"
    EMERGENCY_MEDICINE = "EMERGENCY_MEDICINE"


class EncounterType(str, enum.Enum):
    OUTPATIENT = "OUTPATIENT"
    INPATIENT = "INPATIENT"
    EMERGENCY = "EMERGENCY"


class SourceType(str, enum.Enum):
    PATIENT_REPORTED = "PATIENT_REPORTED"
    INSTITUTION_GENERATED = "INSTITUTION_GENERATED"


class AiSummaryStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SafetyAlertPriority(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AssignmentRole(str, enum.Enum):
    ATTENDING_PHYSICIAN = "ATTENDING_PHYSICIAN"
    CONSULTING_PHYSICIAN = "CONSULTING_PHYSICIAN"  # 협진 관계
    PRIMARY_NURSE = "PRIMARY_NURSE"


class ClinicalReportType(str, enum.Enum):
    DOCTOR_REFERENCE = "DOCTOR_REFERENCE"
    HANDOFF = "HANDOFF"
    PATIENT_EASY = "PATIENT_EASY"


class ClinicalReportScopeType(str, enum.Enum):
    SINGLE_ENCOUNTER = "SINGLE_ENCOUNTER"
    PERIOD = "PERIOD"
    FULL_HISTORY = "FULL_HISTORY"


# AiSummaryStatus와 값이 같은 이름(DRAFT/APPROVED/REJECTED)이지만 별도
# Enum이다 — ClinicalReport는 AiSummary와 별개의 승인 흐름을 가지므로
# 하나의 Enum 클래스를 두 엔티티가 공유하지 않는다.
class ClinicalReportStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# Task F4-A: KR Core IG v1.0.2(STU1)가 공식 Profile로 확인한 7종만 허용한다
# (docs/standards/kr-cdi-kr-core-mapping.md 참고). BMI는 그 7종에 없는
# 계산값이라 별도 VitalType으로 추가하지 않는다 — Backend 공통 서비스가
# 그때그때 계산만 하고 저장하지 않는다(app/services/vital_sign_derived.py).
class VitalType(str, enum.Enum):
    BLOOD_PRESSURE = "BLOOD_PRESSURE"
    BODY_HEIGHT = "BODY_HEIGHT"
    BODY_WEIGHT = "BODY_WEIGHT"
    BODY_TEMPERATURE = "BODY_TEMPERATURE"
    HEART_RATE = "HEART_RATE"
    RESPIRATORY_RATE = "RESPIRATORY_RATE"
    PULSE_OXIMETRY = "PULSE_OXIMETRY"
