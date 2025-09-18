from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    timestamp: datetime


class ProjectInfo(BaseModel):
    name: str
    path: Path
    has_workspace: bool
    workspace_path: Path | None = None


class ProjectListResponse(BaseModel):
    projects: list[ProjectInfo]


class WorkspaceCreateRequest(BaseModel):
    project_path: Path = Field(..., description="Absolute path to the source project")


class WorkspaceDocumentRequest(BaseModel):
    relative_path: Path = Field(..., description="Path within the workspace (e.g. requirements/feature.md.enc)")
    content: str = Field(..., description="UTF-8 text content to encrypt and store")


class WorkspaceDocumentResponse(BaseModel):
    stored_path: Path


class AWSStatusResponse(BaseModel):
    enabled_bedrock: bool
    enabled_s3_sync: bool
    enabled_secrets_manager: bool
    region: str | None | None = None
    profile: str | None | None = None
    identity_arn: str | None | None = None
    account_id: str | None | None = None
    workspace_bucket: Path | None | None = None
    workspace_bucket_exists: bool | None | None = None
    errors: list[str] = []


class BedrockModelsResponse(BaseModel):
    models: list[str]


class BedrockInvokeRequest(BaseModel):
    model_id: str
    prompt: str


class BedrockInvokeResponse(BaseModel):
    model_id: str
    output_text: str
