from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

WORKSPACE_SUBDIRS: tuple[str, ...] = (
    "requirements",
    "designs",
    "tasks",
    "research",
    "outputs",
    "logs",
    "secrets",
)


@dataclass(slots=True, frozen=True)
class Workspace:
    project_path: Path
    workspace_path: Path
    salt: bytes

    @property
    def secrets_path(self) -> Path:
        return self.workspace_path / "secrets"

    @property
    def metadata_file(self) -> Path:
        return self.workspace_path / "workspace.json"

    def directories(self) -> Iterable[Path]:
        yield from (self.workspace_path / subdir for subdir in WORKSPACE_SUBDIRS)
