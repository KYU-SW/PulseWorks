from sqlalchemy import Column, Integer, String, Enum, ForeignKey
from sqlalchemy.orm import relationship

from app.core.db import Base
from app.models.enums import Role, Department


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False)
    department = Column(Enum(Department), nullable=True)
    # Nullable: only role=PATIENT users link to a Patient record.
    # ON DELETE SET NULL: a login account is not itself clinical data, so if
    # its linked Patient row were ever removed the account is not force-deleted.
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    patient = relationship("Patient", back_populates="user_account")
