import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_db


# ---------------------------------------------------------------------------
# 正常系: DB接続成功時に 200 と期待レスポンスを返す
# ---------------------------------------------------------------------------

@pytest.mark.test_db_url("sqlite:///./test_health.db")
def test_health_ok(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


# ---------------------------------------------------------------------------
# 認証不要: トークンなし・get_current_user override なしで 200 を返す
# ---------------------------------------------------------------------------

@pytest.mark.test_db_url("sqlite:///./test_health.db")
def test_health_no_auth_required(db_session_for_test_function):
    """/health は get_current_user に依存しないため、トークンなしで 200 を返す。"""
    from app.main import create_app

    app = create_app()
    # get_db のみ override — get_current_user は override しない
    app.dependency_overrides[get_db] = lambda: db_session_for_test_function

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


# ---------------------------------------------------------------------------
# DB 異常系: execute が失敗したとき 503 を返す
# ---------------------------------------------------------------------------

@pytest.mark.test_db_url("sqlite:///./test_health.db")
def test_health_db_error_returns_503(test_app):
    """`db.execute()` が例外を投げたとき、/health は 503 を返す。"""

    class BrokenDB:
        """execute() が常に例外を投げるモック DB セッション。"""
        def execute(self, *args, **kwargs):
            raise Exception("simulated DB connection failure")

    test_app.dependency_overrides[get_db] = lambda: BrokenDB()

    with TestClient(test_app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "error"}
