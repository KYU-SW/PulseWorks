from sqlalchemy import Column, Integer, String, Date, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.enums import Department, AssignmentRole


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True)
    mrn = Column(String, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)
    # Calendar date only — no time-of-day or timezone concept applies to a
    # birth date, unlike every other timestamp in this schema.
    birth_date = Column(Date, nullable=False)
    sex = Column(String, nullable=False)

    user_account = relationship("User", back_populates="patient", uselist=False)


class PatientAssignment(Base):
    """담당(주치의/협진의) 또는 담당간호사 관계. RBAC의 can_access_patient가
    이 테이블의 존재 여부로 접근을 결정한다 (Task 5)."""

    __tablename__ = "patient_assignments"

    id = Column(Integer, primary_key=True)
    # NOT NULL FK -> ON DELETE RESTRICT: 배정 이력이 남아있는 한 환자/직원
    # 레코드가 실수로 삭제되지 않도록 한다.
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    staff_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    department = Column(Enum(Department), nullable=False)
    assignment_role = Column(Enum(AssignmentRole), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
