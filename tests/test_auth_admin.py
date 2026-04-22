"""
認可（is_admin）の動作確認テスト。

- 一般ユーザーが /ingest/weather・/analysis/{date} にアクセスすると 403 になること
- 管理者は同エンドポイントにアクセスできること
"""
import pytest
from datetime import datetime, timezone

from app import models
from app.core.security import get_password_hash
from app.dependencies import get_db, get_current_user


# ---------------------------------------------------------------------------
# 一般ユーザー専用フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def non_admin_user(db_session_for_test_function):
    user = models.User(
        email="nonadmin@example.com",
        hashed_password=get_password_hash("pass"),
        created_at=datetime.now(timezone.utc),
        is_admin=False,
    )
    db_session_for_test_function.add(user)
    db_session_for_test_function.flush()
    return user


@pytest.fixture(scope="function")
def non_admin_client(test_app, non_admin_user):
    """get_current_user を一般ユーザーで上書きしたクライアント。"""
    from fastapi.testclient import TestClient
    test_app.dependency_overrides[get_current_user] = lambda: non_admin_user
    with TestClient(test_app) as client:
        yield client
    # test_app の override は test_app fixture の teardown で一括 clear される


# ---------------------------------------------------------------------------
# /ingest/weather – admin 限定
# ---------------------------------------------------------------------------

@pytest.mark.test_db_url("sqlite:///./test_admin.db")
def test_weather_ingest_forbidden_for_non_admin(non_admin_client):
    """/ingest/weather は一般ユーザーに 403 を返すこと。"""
    payload = {"date": "2025-01-01", "temp_max": 25.0, "temp_min": 15.0}
    response = non_admin_client.post("/ingest/weather", json=payload)
    assert response.status_code == 403
    assert "管理者権限" in response.json()["detail"]


@pytest.mark.test_db_url("sqlite:///./test_admin.db")
def test_weather_ingest_allowed_for_admin(test_client):
    """/ingest/weather は管理者（test_user, is_admin=True）に 200 を返すこと。"""
    payload = {"date": "2025-01-01", "temp_max": 25.0, "temp_min": 15.0}
    response = test_client.post("/ingest/weather", json=payload)
    assert response.status_code == 200
    assert response.json()["temp_max"] == 25.0


# ---------------------------------------------------------------------------
# /analysis/{date} – admin 限定
# ---------------------------------------------------------------------------

@pytest.mark.test_db_url("sqlite:///./test_admin.db")
def test_analysis_forbidden_for_non_admin(non_admin_client):
    """/analysis/{date} は一般ユーザーに 403 を返すこと。"""
    response = non_admin_client.get("/analysis/2025-01-01")
    assert response.status_code == 403
    assert "管理者権限" in response.json()["detail"]


@pytest.mark.test_db_url("sqlite:///./test_admin.db")
def test_analysis_allowed_for_admin(test_client):
    """/analysis/{date} は管理者に 200 または 404（データなし）を返すこと。"""
    response = test_client.get("/analysis/2030-01-01")
    # データがないので 404 だが、403 ではないことを確認
    assert response.status_code == 404
    assert "Insufficient data" in response.json()["detail"]


# ---------------------------------------------------------------------------
# /auth/setup – 初回管理者作成
# ---------------------------------------------------------------------------

@pytest.mark.test_db_url("sqlite:///./test_admin.db")
def test_setup_blocked_when_admin_exists(test_client):
    """/auth/setup は admin が既に存在する場合 403 を返すこと。"""
    payload = {"email": "newadmin@example.com", "password": "strongpass"}
    response = test_client.post("/auth/setup", json=payload)
    assert response.status_code == 403
    assert "An admin user already exists" in response.json()["detail"]


@pytest.mark.test_db_url("sqlite:///./test_setup.db")
def test_setup_creates_admin_when_none_exists(db_session_for_test_function):
    """/auth/setup は admin が存在しないときに 201 で is_admin=True ユーザーを作成すること。"""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.dependencies import get_db

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session_for_test_function

    with TestClient(app) as client:
        payload = {"email": "firstadmin@example.com", "password": "strongpass"}
        response = client.post("/auth/setup", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "firstadmin@example.com"
    assert data["is_admin"] is True


@pytest.mark.test_db_url("sqlite:///./test_setup.db")
def test_setup_second_call_blocked(db_session_for_test_function):
    """/auth/setup は 2 回目以降 403 を返すこと。"""
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.dependencies import get_db
    from app.core.security import get_password_hash
    from app import models
    from datetime import datetime, timezone

    # 直接 admin を挿入しておく
    admin = models.User(
        email="existing@example.com",
        hashed_password=get_password_hash("pass"),
        created_at=datetime.now(timezone.utc),
        is_admin=True,
    )
    db_session_for_test_function.add(admin)
    db_session_for_test_function.flush()

    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session_for_test_function

    with TestClient(app) as client:
        payload = {"email": "another@example.com", "password": "strongpass"}
        response = client.post("/auth/setup", json=payload)

    assert response.status_code == 403
    assert "An admin user already exists" in response.json()["detail"]
