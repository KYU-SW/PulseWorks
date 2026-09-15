import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.db import Base

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session():
    engine = create_engine(
        TEST_DATABASE_URL, connect_args={"check_same_thread": False}
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
