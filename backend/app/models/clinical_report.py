from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Index, Integer, JSON

from app.core.db import Base
from app.models.enums import ClinicalReportScopeType, ClinicalReportStatus, ClinicalReportType


class ClinicalReport(Base):
    """의사용/환자용 임상 통합 보고서. Task 13은 DRAFT 생성만 다룬다 —
    PATCH/승인/반려는 Task 17, 환자 공개는 Task 19의 몫이다.

    content는 collect_report_data()(Task 12)의 결과를 보고서 생성
    시점에 ReportContentSnapshot으로 검증해 JSON으로 저장한 스냅샷이다.
    조회 시 원본 EMR 데이터를 다시 수집하지 않는다 — 원본이 나중에
    바뀌어도 이미 만든 보고서의 content는 그대로 고정된다.
    """

    __tablename__ = "clinical_reports"
    __table_args__ = (
        # DRAFT는 아직 검토되지 않았으므로 reviewed_at이 없어야 하고,
        # APPROVED/REJECTED는 반드시 검토 시각을 가져야 한다.
        # reviewed_by_user_id는 여기서 함께 NOT NULL을 강제하지 않는다 —
        # 그 컬럼은 ON DELETE SET NULL이라, User가 삭제되면 이 CHECK와
        # 충돌하게 된다. 승인/반려 시 검토자 ID를 반드시 채우는 규칙은
        # Task 17의 서비스 로직/테스트가 담당한다.
        CheckConstraint(
            "(status = 'DRAFT' AND reviewed_at IS NULL) OR "
            "(status IN ('APPROVED', 'REJECTED') AND reviewed_at IS NOT NULL)",
            name="ck_clinical_report_reviewed_at_matches_status",
        ),
        # SINGLE_ENCOUNTER는 encounter_id가 있어야 하고, PERIOD/
        # FULL_HISTORY는 (아직 다중 Encounter 참조 컬럼이 없으므로) 없어야
        # 한다. scope_encounter_ids JSON 배열의 길이·일치 여부는 DB CHECK가
        # 아니라 서비스/테스트에서 보장한다.
        CheckConstraint(
            "(scope_type = 'SINGLE_ENCOUNTER' AND encounter_id IS NOT NULL) OR "
            "(scope_type IN ('PERIOD', 'FULL_HISTORY') AND encounter_id IS NULL)",
            name="ck_clinical_report_scope_encounter",
        ),
        CheckConstraint(
            "supersedes_report_id IS NULL OR supersedes_report_id <> id",
            name="ck_clinical_report_no_self_supersede",
        ),
        # 환자별 보고서 목록 조회와 중복 DRAFT 검색(같은 환자/유형/스코프/
        # 상태 조합)에 사용하는 복합 인덱스.
        Index(
            "ix_clinical_reports_patient_type_scope_status",
            "patient_id",
            "report_type",
            "scope_type",
            "status",
        ),
    )

    id = Column(Integer, primary_key=True)
    patient_id = Column(
        Integer,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # SINGLE_ENCOUNTER 스코프에서만 채워진다(위 CHECK 참고). PERIOD/
    # FULL_HISTORY 스코프는 여러 Encounter를 다루므로 이 단일 FK로는
    # 표현하지 않는다 — 그 스코프들은 scope_encounter_ids만 사용한다.
    encounter_id = Column(
        Integer,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    report_type = Column(Enum(ClinicalReportType), nullable=False)
    scope_type = Column(Enum(ClinicalReportScopeType), nullable=False)
    # 보고서 생성 당시 확정된 Encounter ID 목록(list[int]) — 원본이
    # 나중에 바뀌어도 이 목록은 그대로 고정된다.
    scope_encounter_ids = Column(JSON, nullable=False)
    status = Column(Enum(ClinicalReportStatus), nullable=False, default=ClinicalReportStatus.DRAFT)
    # ReportContentSnapshot.model_dump(mode="json") 결과.
    content = Column(JSON, nullable=False)
    created_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False)
    last_modified_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # onupdate=func.now()를 쓰지 않는다 — 승인/반려(reviewed_at)와 구분되는
    # "서술형 필드가 실제로 수정된 시각"만을 뜻하며, Task 17에서 PATCH가
    # 일어날 때만 애플리케이션이 명시적으로 갱신한다.
    last_modified_at = Column(DateTime(timezone=True), nullable=False)
    reviewed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    supersedes_report_id = Column(
        Integer,
        ForeignKey("clinical_reports.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
