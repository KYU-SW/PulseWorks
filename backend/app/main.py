from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.routers import auth, patients

app = FastAPI(title="EMR Prototype")

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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(patients.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
