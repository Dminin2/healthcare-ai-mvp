import pytest
import os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, session
from datetime import datetime, date, timezone, timedelta

from app.db import Base
from app.dependencies import get_db, get_current_user
from app.routers import ingest, summary, analysis, advice
from app import models
from app.core import analysis_logic
from app.core.security import get_password_hash


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "test_db_url(url): specify the database URL for the test module"
    )


# ---------------------------------------------------------------------------
# DB setup (module-scoped – one SQLite file per test module)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def setup_db_for_module(request):
    test_db_url = request.node.get_closest_marker("test_db_url")
    db_url = test_db_url.args[0] if test_db_url else "sqlite:///./default_module_test.db"

    db_file = db_url.replace("sqlite:///./", "")
    if os.path.exists(db_file):
        os.remove(db_file)

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    yield db_url, engine, TestingSessionLocal

    Base.metadata.drop_all(bind=engine)
    if os.path.exists(db_file):
        os.remove(db_file)


@pytest.fixture(scope="function")
def db_session_for_test_function(setup_db_for_module):
    _, engine, TestingSessionLocal = setup_db_for_module

    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


# ---------------------------------------------------------------------------
# Test user (created fresh per function, rolled back with the session)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_user(db_session_for_test_function):
    """Creates and returns a test User in the test DB."""
    user = models.User(
        email="test@example.com",
        hashed_password=get_password_hash("testpassword"),
        created_at=datetime.now(timezone.utc),
        is_admin=True,
    )
    db_session_for_test_function.add(user)
    db_session_for_test_function.flush()  # populate user.id without committing
    return user


# ---------------------------------------------------------------------------
# App + test client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def test_app(db_session_for_test_function, test_user):
    from app.main import create_app
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session_for_test_function
    # Bypass JWT validation in tests – always return the test user
    app.dependency_overrides[get_current_user] = lambda: test_user
    yield app
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_client(test_app: FastAPI, monkeypatch):
    """TestClient with LLM disabled."""
    original_llm_provider = os.environ.pop("LLM_PROVIDER", None)
    with TestClient(test_app) as client:
        yield client
    if original_llm_provider is not None:
        os.environ["LLM_PROVIDER"] = original_llm_provider


# ---------------------------------------------------------------------------
# Generic test dataset (40 days of synthetic data for a single user)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def populate_generic_test_data(db_session_for_test_function, test_user):
    """Populates 40 days of synthetic health + weather data for the test user."""
    db = db_session_for_test_function
    user_id = test_user.id
    today = date(2025, 12, 20)

    data = []
    for i in range(40):
        d = today - timedelta(days=i)
        temp_max = 20.0 + (i % 10)
        symptoms, mood = ["none"], 5

        if i in [1, 5, 9, 13]:
            temp_max, symptoms, mood = 34.0, ["fatigue"], 3
        if i == 2:
            temp_max = 20.0
        if i == 11:
            mood, symptoms = 2, ["headache"]

        data.append(models.Weather(
            date=d,
            temp_max=temp_max, temp_min=temp_max - 10,
            precipitation_sum=float(i % 10),
        ))

        sleep = 4.5 if i == 0 else 7.5
        data.append(models.SleepSession(
            user_id=user_id,
            session_start_time=datetime.combine(
                d - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
            ) + timedelta(hours=22),
            session_end_time=datetime.combine(
                d, datetime.min.time(), tzinfo=timezone.utc
            ) + timedelta(hours=6),
            total_sleep_hours=sleep,
            created_at=datetime.now(timezone.utc),
        ))

        data.append(models.StepCount(
            user_id=user_id,
            timestamp=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
            value=10000 + (-1) ** i * 2000,
        ))

        data.append(models.RestingHeartRate(
            user_id=user_id,
            timestamp=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
            value=60 + (i % 7),
        ))

        data.append(models.DailyState(
            user_id=user_id, date=d, mood=mood, symptoms=symptoms,
        ))

    db.add_all(data)
    db.commit()
    return today
