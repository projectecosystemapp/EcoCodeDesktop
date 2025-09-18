from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from eco_api import __version__
from eco_api.aws import AWSClient
from eco_api.config import Settings, get_settings
from eco_api.logging import configure_logging
from eco_api.schemas import (
    AWSStatusResponse,
    BedrockInvokeRequest,
    BedrockInvokeResponse,
    BedrockModelsResponse,
    HealthResponse,
    ProjectInfo,
    ProjectListResponse,
    WorkspaceCreateRequest,
    WorkspaceDocumentRequest,
    WorkspaceDocumentResponse,
)
from eco_api.workspaces.manager import WorkspaceManager

configure_logging()
logger = logging.getLogger(__name__)
app = FastAPI(title="EcoCode Orchestrator", version=__version__)


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_workspace_manager(settings: SettingsDep) -> WorkspaceManager:
    return WorkspaceManager(settings=settings)


WorkspaceManagerDep = Annotated[WorkspaceManager, Depends(get_workspace_manager)]


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, timestamp=datetime.now(UTC))


@app.get("/projects", response_model=ProjectListResponse)
def list_projects(settings: SettingsDep) -> ProjectListResponse:
    manager = WorkspaceManager(settings=settings)
    projects = []
    for project_path in manager.discover_projects():
        workspace_path = settings.workspace_path_for(project_path)
        metadata_path = workspace_path / "workspace.json"
        has_workspace = metadata_path.exists()
        logger.debug("Discovered project", extra={"project_path": str(project_path), "has_workspace": has_workspace})
        projects.append(
            ProjectInfo(
                name=project_path.name,
                path=project_path,
                has_workspace=has_workspace,
                workspace_path=workspace_path if has_workspace else None,
            )
        )
    return ProjectListResponse(projects=projects)


@app.post("/workspaces", response_model=ProjectInfo, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreateRequest,
    manager: WorkspaceManagerDep,
) -> ProjectInfo:
    try:
        workspace = manager.create_workspace(payload.project_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    logger.info("Workspace created", extra={"project_path": str(workspace.project_path)})
    return ProjectInfo(
        name=workspace.project_path.name,
        path=workspace.project_path,
        has_workspace=True,
        workspace_path=workspace.workspace_path,
    )


@app.post(
    "/workspaces/{workspace_name}/documents",
    response_model=WorkspaceDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def write_workspace_document(
    workspace_name: str,
    payload: WorkspaceDocumentRequest,
    manager: WorkspaceManagerDep,
) -> WorkspaceDocumentResponse:
    workspace_dir = Path(manager.projects_root / workspace_name)
    metadata_path = workspace_dir / "workspace.json"
    if not metadata_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workspace {workspace_name} not found",
        )

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    project_path = Path(metadata["projectPath"])
    workspace = manager.workspace_for(project_path)

    relative_path = payload.relative_path
    if relative_path.is_absolute():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="relative_path must be relative to the workspace root",
        )
    if relative_path.suffix != ".enc":
        relative_path = relative_path.with_suffix(relative_path.suffix + ".enc")

    stored_path = manager.write_encrypted(
        workspace,
        relative_path,
        payload.content.encode("utf-8"),
    )
    return WorkspaceDocumentResponse(stored_path=stored_path)



@app.get("/aws/status", response_model=AWSStatusResponse)
def aws_status(settings: SettingsDep) -> AWSStatusResponse:
    """Return AWS configuration/status using default credentials/profile.

    This endpoint does not fail the service if AWS is not configured; it reports
    whatever can be detected so the desktop can guide the user.
    """
    aws_client = AWSClient(settings.aws)
    st = aws_client.status()
    bucket_path = Path(settings.aws.workspace_bucket) if settings.aws.workspace_bucket else None
    return AWSStatusResponse(
        enabled_bedrock=settings.aws.use_bedrock,
        enabled_s3_sync=settings.aws.use_s3_sync,
        enabled_secrets_manager=settings.aws.use_secrets_manager,
        region=st.region,
        profile=st.profile,
        identity_arn=st.identity_arn,
        account_id=st.account_id,
        workspace_bucket=bucket_path,
        workspace_bucket_exists=st.workspace_bucket_exists,
        errors=st.errors,
    )



@app.get("/aws/bedrock/models", response_model=BedrockModelsResponse)
def aws_bedrock_models(settings: SettingsDep) -> BedrockModelsResponse:
    if not settings.aws.use_bedrock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bedrock is disabled")
    client = AWSClient(settings.aws)
    models = client.list_bedrock_models()
    return BedrockModelsResponse(models=models)


@app.post("/aws/bedrock/invoke", response_model=BedrockInvokeResponse)
def aws_bedrock_invoke(
    payload: BedrockInvokeRequest,
    settings: SettingsDep,
) -> BedrockInvokeResponse:
    if not settings.aws.use_bedrock:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bedrock is disabled")
    client = AWSClient(settings.aws)
    text = client.invoke_bedrock_text(payload.model_id, payload.prompt)
    if text is None:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Bedrock invocation failed")
    return BedrockInvokeResponse(model_id=payload.model_id, output_text=text)
