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
    region: str | None = None
    profile: str | None = None
    identity_arn: str | None = None
    account_id: str | None = None
    workspace_bucket: Path | None = None
    workspace_bucket_exists: bool | None = None
    errors: list[str] = Field(default_factory=list)


class BedrockModelsResponse(BaseModel):
    models: list[str]


class BedrockInvokeRequest(BaseModel):
    model_id: str
    prompt: str


class BedrockInvokeResponse(BaseModel):
    model_id: str
    output_text: str


# Spec-driven workflow schemas
class CreateSpecRequest(BaseModel):
    feature_idea: str = Field(..., min_length=3, max_length=500, description="The rough feature idea")
    feature_name: str | None = Field(None, description="Optional explicit feature name (will be generated if not provided)")


class SpecResponse(BaseModel):
    id: str
    feature_name: str
    current_phase: str
    status: str
    created_at: datetime
    updated_at: datetime
    progress: float = Field(ge=0.0, le=1.0)


class SpecListResponse(BaseModel):
    specs: list[SpecResponse]
    total_count: int


class SpecDetailResponse(BaseModel):
    id: str
    feature_name: str
    current_phase: str
    status: str
    created_at: datetime
    updated_at: datetime
    progress: float = Field(ge=0.0, le=1.0)
    documents: dict[str, str | None] = Field(default_factory=dict)
    approvals: dict[str, str] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class UpdateDocumentRequest(BaseModel):
    content: str = Field(..., description="The document content in markdown format")
    approve: bool | None = Field(None, description="Whether to approve the current phase")
    feedback: str | None = Field(None, description="Optional feedback for the update")


class UpdateDocumentResponse(BaseModel):
    success: bool
    message: str
    updated_at: datetime
    checksum: str


class ExecuteTaskRequest(BaseModel):
    task_description: str | None = Field(None, description="Optional task description for validation")


class ExecuteTaskResponse(BaseModel):
    success: bool
    message: str
    task_id: str
    status: str
    execution_log: list[str] = Field(default_factory=list)


class UpdateTaskStatusRequest(BaseModel):
    status: str = Field(..., description="New task status (not_started, in_progress, completed, blocked)")


class UpdateTaskStatusResponse(BaseModel):
    success: bool
    message: str
    task_id: str
    status: str
    updated_at: datetime


class ProgressResponse(BaseModel):
    spec_id: str
    total_tasks: int
    completed_tasks: int
    in_progress_tasks: int
    not_started_tasks: int
    blocked_tasks: int
    progress_percentage: float = Field(ge=0.0, le=100.0)
    current_phase: str
    status: str


class ApprovePhaseRequest(BaseModel):
    approved: bool = Field(..., description="Whether to approve or reject the phase")
    feedback: str | None = Field(None, description="Optional feedback for the approval/rejection")


class ApprovePhaseResponse(BaseModel):
    success: bool
    message: str
    phase: str
    approved: bool
    updated_at: datetime


class WorkflowStatusResponse(BaseModel):
    spec_id: str
    current_phase: str
    status: str
    created_at: datetime
    updated_at: datetime
    approvals: dict[str, str] = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)
    valid_transitions: list[str] = Field(default_factory=list)
