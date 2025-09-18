from __future__ import annotations

import io
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from eco_api.config import get_settings
from eco_api.main import app


@pytest.fixture(autouse=True)
def configure_env(monkeypatch: pytest.MonkeyPatch):
    # Required base settings
    monkeypatch.setenv("ECOCODE_MASTER_PASSPHRASE", "test-passphrase")
    # Enable bedrock by default in these tests; individual tests can override
    monkeypatch.setenv("ECOCODE_AWS_USE_BEDROCK", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def api_client() -> TestClient:
    return TestClient(app)


class _FakeBedrock:
    def list_foundation_models(self, **_: Any):
        return {
            "modelSummaries": [
                {"modelId": "anthropic.claude-3-haiku-20240307-v1:0"},
                {"modelId": "amazon.titan-text-express-v1"},
            ]
        }


class _FakeBedrockRuntime:
    def invoke_model(self, *, modelId: str, body: bytes | str, **kwargs: Any):
        if isinstance(body, (bytes, bytearray)):
            data = json.loads(body.decode("utf-8"))
        else:
            data = json.loads(body)
        prompt = data.get("inputText") or data.get("prompt") or ""
        payload = json.dumps({"outputText": f"Echo: {prompt}", "modelId": modelId}).encode(
            "utf-8"
        )
        return {"body": io.BytesIO(payload), "contentType": "application/json"}


class _FakeSession:
    def __init__(self, *_, **__):
        pass

    def client(self, service: str):
        if service == "bedrock":
            return _FakeBedrock()
        if service == "bedrock-runtime":
            return _FakeBedrockRuntime()
        raise ValueError(f"unexpected service {service}")


@pytest.fixture()
def mock_boto3_session(monkeypatch: pytest.MonkeyPatch):
    # Patch boto3 Session used within eco_api.aws to our fake
    import eco_api.aws as aws_mod

    monkeypatch.setattr(aws_mod.boto3, "Session", _FakeSession)
    return _FakeSession


def test_bedrock_disabled_returns_404(api_client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ECOCODE_AWS_USE_BEDROCK", "false")
    get_settings.cache_clear()

    r1 = api_client.get("/aws/bedrock/models")
    assert r1.status_code == 404

    r2 = api_client.post("/aws/bedrock/invoke", json={"model_id": "x", "prompt": "hi"})
    assert r2.status_code == 404


def test_list_bedrock_models(api_client: TestClient, mock_boto3_session):
    resp = api_client.get("/aws/bedrock/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data
    assert data["models"][0] == "anthropic.claude-3-haiku-20240307-v1:0"
    assert "amazon.titan-text-express-v1" in data["models"]


def test_invoke_bedrock_text(api_client: TestClient, mock_boto3_session):
    payload = {"model_id": "anthropic.claude-3-haiku-20240307-v1:0", "prompt": "Hello"}
    resp = api_client.post("/aws/bedrock/invoke", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["output_text"].startswith("Echo: Hello")
    assert data["model_id"] == payload["model_id"]
