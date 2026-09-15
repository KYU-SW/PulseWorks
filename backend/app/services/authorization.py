from sqlalchemy.orm import Session

from app.models import PatientAssignment, Role, User


def can_access_patient(user: User, patient_id: int, db: Session) -> bool:
    """Central authorization rule for all patient-scoped *clinical* resources
    (timeline, lab results, prescriptions, AI summaries, audit logs, ...).
    Every later router that touches patient clinical data must call this —
    role checks alone (`require_roles`) are not enough, and a resource
    check must never be re-implemented ad hoc per endpoint.

    PATIENT: only their own linked patient_id. Every other patient is
        always denied, unconditionally.
    DOCTOR/NURSE: only patients with an active PatientAssignment to them.
        Being in the *same department* as the patient's care team is not
        sufficient by itself — an actual assignment row is required. No
        distinction is made here between assignment roles (attending vs.
        consulting physician; primary nurse) — any assignment row is
        sufficient, because the assignment itself is what "담당 또는 협진
        관계" and "배정" require. Which clinical actions a NURSE vs a
        DOCTOR may take once access is granted (e.g. NURSE cannot
        prescribe or approve AI summaries) is enforced separately by
        `require_roles` on each endpoint, not by this function.
    ADMIN_STAFF/SYSTEM_ADMIN: always False. Neither role has default
        access to clinical record content — ADMIN_STAFF's scope is
        front-desk/scheduling/basic administrative info, SYSTEM_ADMIN's
        scope is accounts/roles/system settings. Being ADMIN_STAFF or
        SYSTEM_ADMIN must never by itself satisfy this check; if a future
        administrative feature needs access to non-clinical fields (e.g.
        scheduling), it must use its own, separately-scoped authorization
        check rather than this one.

    Note for callers that expose this over HTTP: to avoid leaking whether
    a given patient_id even exists, a denied check should normally result
    in the same 403 response regardless of whether the patient is real or
    not — don't distinguish "not found" from "not yours" in the response.
    """
    if user.role == Role.PATIENT:
        return user.patient_id == patient_id

    if user.role in (Role.DOCTOR, Role.NURSE):
        assignment = (
            db.query(PatientAssignment)
            .filter_by(patient_id=patient_id, staff_user_id=user.id)
            .first()
        )
        return assignment is not None

    return False
