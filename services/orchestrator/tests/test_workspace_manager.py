from __future__ import annotations

import json
from pathlib import Path

import pytest

from eco_api.config import Settings
from eco_api.workspaces.manager import WorkspaceManager


@pytest.fixture()
def settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    project_dir = tmp_path / "demo-project"
    project_dir.mkdir()
    (project_dir / "package.json").write_text("{}", encoding="utf-8")

    monkeypatch.setenv("ECOCODE_MASTER_PASSPHRASE", "super-secure-passphrase")
    monkeypatch.setenv("ECOCODE_PROJECTS_ROOT", str(tmp_path))

    return Settings()


def test_create_workspace(settings: Settings) -> None:
    manager = WorkspaceManager(settings=settings)
    project_path = settings.projects_root / "demo-project"

    workspace = manager.create_workspace(project_path)

    assert workspace.workspace_path.exists()
    assert (workspace.workspace_path / "workspace.json").exists()
    for subdir in (workspace.workspace_path / name for name in ("requirements", "designs", "tasks", "research", "outputs", "logs", "secrets")):
        assert subdir.exists()

    metadata = json.loads((workspace.workspace_path / "workspace.json").read_text(encoding="utf-8"))
    assert metadata["projectPath"] == str(project_path)
    assert metadata["encryption"]["algorithm"] == "AES-256-GCM"


def test_encrypted_roundtrip(settings: Settings, tmp_path: Path) -> None:
    manager = WorkspaceManager(settings=settings)
    project_path = settings.projects_root / "demo-project"
    workspace = manager.create_workspace(project_path)

    payload = "Confidential spec content"
    encrypted_path = manager.write_encrypted(workspace, Path("requirements/user-story-1.md.enc"), payload.encode("utf-8"))

    assert encrypted_path.exists()
    raw_bytes = encrypted_path.read_bytes()
    assert raw_bytes != payload.encode("utf-8")

    decrypted = manager.read_encrypted(workspace, Path("requirements/user-story-1.md.enc"))
    assert decrypted.decode("utf-8") == payload
