from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.routers import (
    auth,
    clinical_reports,
    encounters,
    lab_trends,
    patient_reports,
    patients,
    prescriptions,
)
from app.services.cda.errors import validate_cda_settings


def validate_cda_startup_config() -> None:
    """HL7-4A.1 Gate 3: CDA_ENABLED=true인데 설정이 잘못되면 요청이
    들어올 때까지 방치하지 않고 앱 기동 시점에 즉시 실패한다(fail
    fast). CDA_ENABLED=false면 validate_cda_settings() 자체가 아무것도
    하지 않으므로(HL7-3 §14) 기존 Backend 기동에는 영향이 없다 -
    narrative_provider가 기동을 막지 않는 것과 동일한 선례를 따르되,
    CDA는 "활성화된 상태에서의 잘못된 설정"만큼은 기동 시점에 걸러낸다
    (HL7-4A.1 §10 승인된 정책)."""
    validate_cda_settings(get_settings())


app = FastAPI(title="EMR Prototype")
validate_cda_startup_config()

# Dev-only CORS: the React dev server (localhost:5173) is a different
# origin from FastAPI (localhost:8000), so the browser needs an explicit
# allow-list — not allow_origins=["*"]. allow_credentials stays False since
# auth here is a Bearer token in a header, not a cookie. When this moves
# beyond local dev, the allowed origin(s) should come from an environment
# variable rather than being hardcoded here (see README's CORS section).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(encounters.router)
app.include_router(prescriptions.router)
app.include_router(lab_trends.router)
app.include_router(clinical_reports.patient_reports_router)
app.include_router(clinical_reports.reports_router)
app.include_router(patient_reports.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
