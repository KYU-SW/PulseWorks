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
