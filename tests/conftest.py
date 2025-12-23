import pytest
import os
import sys # Import sys
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, session
from unittest.mock import MagicMock
from datetime import datetime, date, timezone, timedelta
from unittest.mock import MagicMock
import sys # Added for sys.modules mocking




# Import modules from the main application
from app.db import Base
from app.dependencies import get_db
from app.routers import ingest, summary, analysis, advice
from app import models # models needs to be imported here for Base.metadata.create_all
from app.core import analysis_logic


# Register custom marker for database URL
def pytest_configure(config):
    config.addinivalue_line("markers", "test_db_url(url): specify the database URL for the test module")


# --- Global Test Database Setup (managed by fixtures) ---

@pytest.fixture(scope="module")
def setup_db_for_module(request):
    """
    Sets up a unique SQLite database file for the entire test module,
    creates tables, and cleans up the file after all tests in the module are done.
    """
    test_db_url = request.node.get_closest_marker("test_db_url")
    if test_db_url:
        db_url = test_db_url.args[0]
    else:
        db_url = "sqlite:///./default_module_test.db"

    # Ensure the DB file is clean before starting
    if os.path.exists(db_url.replace("sqlite:///./", "")):
        os.remove(db_url.replace("sqlite:///./", ""))

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine) # Create tables for this module's DB

    yield db_url, engine, TestingSessionLocal # Provide engine and session factory to subsequent fixtures

    Base.metadata.drop_all(bind=engine) # Drop tables after module tests
    if os.path.exists(db_url.replace("sqlite:///./", "")):
        os.remove(db_url.replace("sqlite:///./", ""))


@pytest.fixture(scope="function")
def db_session_for_test_function(setup_db_for_module):
    """
    Provides a transactional SQLAlchemy session for each test function within the module's DB.
    Rolls back changes after each test.
    """
    _, engine, TestingSessionLocal = setup_db_for_module # Get engine and session factory from module-scoped fixture

    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def test_app(db_session_for_test_function: session.Session):
    from app.main import create_app
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session_for_test_function
    yield app
    app.dependency_overrides.clear()

    print("\n--- APP ROUTES ---")
    for route in app.routes:
        if hasattr(route, "path"): # Check if route has a path attribute
            print(f"Path: {route.path}")
        elif hasattr(route, "routes"): # For APIRouter, it might have nested routes
            for nested_route in route.routes:
                if hasattr(nested_route, "path"):
                    print(f"Nested Path: {nested_route.path}")
    print("--- END APP ROUTES ---\n")

    # Override the get_db dependency to use the test session
    app.dependency_overrides[get_db] = lambda: db_session_for_test_function

    # yield app
    app.dependency_overrides.clear() # Clear overrides after the test

@pytest.fixture(scope="function")
def test_client(test_app: FastAPI, monkeypatch):
    """Provides a TestClient for making requests against the test app."""
    # Ensure LLM_PROVIDER is not set, forcing the fallback mechanism by default
    original_llm_provider = os.environ.pop("LLM_PROVIDER", None)

    with TestClient(test_app) as client:
        yield client

    # Restore original LLM_PROVIDER after test
    if original_llm_provider is not None:
        os.environ["LLM_PROVIDER"] = original_llm_provider


# Fixture for populating data (can be refined per test module if needed)
@pytest.fixture(scope="function")
def populate_generic_test_data(db_session_for_test_function: session.Session):
    """A generic fixture to populate the DB with a rich dataset for analysis."""
    db_session = db_session_for_test_function
    today = date(2025, 12, 20)
    data = []
    for i in range(40):
        d = today - timedelta(days=i)
        temp_max = 20.0 + (i % 10)
        symptoms, mood = ["none"], 5
        if i in [1, 5, 9, 13]: temp_max, symptoms, mood = 34.0, ["fatigue"], 3
        if i == 2: temp_max = 20.0
        if i == 11: mood, symptoms = 2, ["headache"]
        data.append(models.Weather(date=d, temp_max=temp_max, temp_min=temp_max - 10, precipitation_sum=float(i % 10)))
        sleep = 4.5 if i == 0 else 7.5
        data.append(models.SleepSession(session_start_time=datetime.combine(d - timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=22), session_end_time=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=6), total_sleep_hours=sleep, created_at=datetime.now(timezone.utc)))
        data.append(models.StepCount(timestamp=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc), value=10000 + (-1)**i * 2000))
        data.append(models.RestingHeartRate(timestamp=datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc), value=60 + (i % 7)))
        data.append(models.DailyState(date=d, mood=mood, symptoms=symptoms))
    db_session.add_all(data)
    db_session.commit()
    return today
