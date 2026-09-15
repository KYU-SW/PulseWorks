from datetime import date

from pydantic import BaseModel


class AssignedPatientOut(BaseModel):
    """담당 환자 목록에 필요한 최소 필드만 노출한다 — 임상기록 본문,
    다른 의료진 정보, 비밀번호/해시는 포함하지 않는다."""

    id: int
    mrn: str
    name: str
    birth_date: date
    assignment_role: str
