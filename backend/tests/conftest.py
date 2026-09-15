import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session():
    # StaticPool: a plain SQLite ":memory:" database only lives as long as
    # the one connection that created it — without StaticPool, SQLAlchemy's
    # default pooling can hand out a *different* connection (e.g. when a
    # FastAPI TestClient request runs the route in a worker thread), which
    # gets its own empty database ("no such table: ..."). StaticPool pins
    # the whole engine to a single shared connection regardless of thread.
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # SQLite ignores foreign key constraints (including ON DELETE behavior)
    # unless explicitly turned on per connection. Turning it on lets tests
    # verify the RESTRICT/SET NULL policies defined on the models.
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    # expire_on_commit=False: SQLite's DATETIME storage does not actually
    # preserve timezone offsets (unlike Postgres's real timestamptz), so a
    # default session would re-read a naive datetime from disk after every
    # commit. Keeping already-committed Python objects in memory instead of
    # re-querying lets tests correctly assert that the *application* set
    # timezone-aware datetimes, independent of this SQLite storage quirk.
    TestingSessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture()
def override_get_db(db_session):
    """Makes the FastAPI app under test use this test's SQLite db_session
    instead of the real Postgres, for any test that goes through TestClient
    (i.e. exercises real HTTP routing/dependency injection, not just plain
    function calls)."""
    from app.core.db import get_db
    from app.main import app

    def _get_db_override():
        yield db_session

    app.dependency_overrides[get_db] = _get_db_override
    yield
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_test_client(db_session):
    """A small, standalone FastAPI app (separate from app.main) that exists
    purely to exercise get_current_user/require_roles through a real HTTP
    request/response cycle (header parsing, actual 401/403 status codes) —
    Task 5 does not add any protected business endpoint of its own, so this
    is test-only infrastructure, not a production route."""
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from app.core.db import get_db
    from app.core.deps import get_current_user, require_roles
    from app.models import Role

    test_app = FastAPI()

    @test_app.get("/protected")
    def protected(user=Depends(get_current_user)):
        return {"user_id": user.id, "role": user.role.value}

    @test_app.get("/doctors-only")
    def doctors_only(user=Depends(require_roles(Role.DOCTOR))):
        return {"ok": True}

    def _get_db_override():
        yield db_session

    test_app.dependency_overrides[get_db] = _get_db_override
    return TestClient(test_app)
