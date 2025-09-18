from fastapi.testclient import TestClient

from eco_api.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data.get("version"), str)
    assert "timestamp" in data
