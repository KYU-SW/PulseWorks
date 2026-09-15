from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import AuditLog


def write_audit_log(
    db: Session,
    actor_user_id: int,
    action: str,
    resource_type: str,
    resource_id: str,
    reason: str,
    patient_id: int | None = None,
) -> None:
    """Append a row to the audit trail. AuditLog is append-only (see 감사
    로그 정책) — nothing in this codebase should ever UPDATE or DELETE a
    row written here.

    Note: AuditLog.actor_user_id is NOT NULL (Task 3), so this can only
    log actions taken by an *authenticated* user. A failed login attempt
    (wrong password, or an email that doesn't exist at all) has no such
    user to attribute the row to, so it is intentionally not logged here —
    see the Task 5 completion report for why this is a known, reported
    limitation rather than a silent gap.
    """
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            patient_id=patient_id,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
    )
