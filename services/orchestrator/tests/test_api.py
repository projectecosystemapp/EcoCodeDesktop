from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from eco_api.config import get_settings
from eco_api.main import app


@pytest.fixture(autouse=True)
def configure_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('ECOCODE_MASTER_PASSPHRASE', 'super-secure-passphrase')
    monkeypatch.setenv('ECOCODE_PROJECTS_ROOT', str(tmp_path))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint():
    response = client().get('/health')
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'ok'
    assert 'version' in payload


def test_project_listing_and_workspace_creation(tmp_path: Path):
    project_dir = tmp_path / 'demo'
    project_dir.mkdir()
    (project_dir / 'package.json').write_text('{}', encoding='utf-8')

    api_client = client()
    list_response = api_client.get('/projects')
    assert list_response.status_code == 200
    projects = list_response.json()['projects']
    assert len(projects) == 1
    assert projects[0]['has_workspace'] is False

    create_response = api_client.post('/workspaces', json={'project_path': str(project_dir)})
    assert create_response.status_code == 201
    created = create_response.json()
    assert created['has_workspace'] is True

    follow_up = api_client.get('/projects')
    assert follow_up.status_code == 200
    refreshed = follow_up.json()['projects'][0]
    assert refreshed['has_workspace'] is True

