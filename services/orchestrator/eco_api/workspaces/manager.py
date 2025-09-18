from __future__ import annotations

import base64
import json
from datetime import UTC, datetime
from pathlib import Path

from eco_api.config import Settings
from eco_api.security.crypto import WorkspaceCipher, build_cipher, generate_salt
from eco_api.workspaces.models import WORKSPACE_SUBDIRS, Workspace


class WorkspaceManager:
    """Handles encrypted workspace lifecycle operations."""

    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings

    @property
    def projects_root(self) -> Path:
        return self._settings.projects_root.expanduser().resolve()

    def discover_projects(self) -> list[Path]:
        markers = {"package.json", "pyproject.toml", "requirements.txt", "Cargo.toml"}
        projects: list[Path] = []
        for candidate in self.projects_root.iterdir():
            if not candidate.is_dir():
                continue
            if any((candidate / marker).exists() for marker in markers):
                projects.append(candidate)
            elif (candidate / ".git").is_dir():
                projects.append(candidate)
        return sorted(projects)

    def workspace_for(self, project_path: Path) -> Workspace:
        project_path = project_path.expanduser().resolve()
        workspace_path = self._settings.workspace_path_for(project_path)
        metadata_path = workspace_path / "workspace.json"
        if not metadata_path.exists():
            raise FileNotFoundError(
                f"Workspace metadata missing for project {project_path}. Create workspace first."
            )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        salt = base64.b64decode(metadata["salt"], validate=True)
        return Workspace(project_path=project_path, workspace_path=workspace_path, salt=salt)

    def create_workspace(self, project_path: Path) -> Workspace:
        project_path = project_path.expanduser().resolve()
        if not project_path.exists():
            raise FileNotFoundError(f"Project path {project_path} does not exist")
        workspace_path = self._settings.workspace_path_for(project_path)
        workspace_path.mkdir(parents=True, exist_ok=True)

        metadata_path = workspace_path / "workspace.json"
        if metadata_path.exists():
            return self.workspace_for(project_path)

        salt = generate_salt()
        workspace = Workspace(project_path=project_path, workspace_path=workspace_path, salt=salt)
        for directory in workspace.directories():
            directory.mkdir(parents=True, exist_ok=True)

        metadata = {
            "projectPath": str(project_path),
            "salt": base64.b64encode(salt).decode("ascii"),
            "createdAt": datetime.now(UTC).isoformat(),
            "encryption": {
                "algorithm": "AES-256-GCM",
                "kdf": "scrypt",
                "nonceLength": 12,
                "saltLength": len(salt),
            },
        }
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return workspace

    def cipher_for(self, workspace: Workspace) -> WorkspaceCipher:
        return build_cipher(self._settings.master_passphrase, workspace.salt)

    def write_encrypted(self, workspace: Workspace, relative_path: Path, data: bytes) -> Path:
        target_encrypted = workspace.workspace_path / relative_path
        cipher = self.cipher_for(workspace)
        encrypted_payload = cipher.encrypt_bytes(data)
        target_encrypted.parent.mkdir(parents=True, exist_ok=True)
        target_encrypted.write_bytes(encrypted_payload)
        return target_encrypted

    def read_encrypted(self, workspace: Workspace, relative_path: Path) -> bytes:
        encrypted_path = workspace.workspace_path / relative_path
        payload = encrypted_path.read_bytes()
        cipher = self.cipher_for(workspace)
        return cipher.decrypt_bytes(payload)

    def list_workspace_files(self, workspace: Workspace) -> list[Path]:
        results: list[Path] = []
        for subdir in WORKSPACE_SUBDIRS:
            for file in (workspace.workspace_path / subdir).rglob("*.enc"):
                results.append(file)
        return results

    def ensure_structure(self, workspace: Workspace) -> None:
        for directory in workspace.directories():
            directory.mkdir(parents=True, exist_ok=True)
