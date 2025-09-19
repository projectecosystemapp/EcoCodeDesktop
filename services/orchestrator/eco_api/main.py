from __future__ import annotations

import json
import logging
import os
import sys
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
from eco_api.specs.router import router as specs_router
from eco_api.security.security_init import quick_setup_security

# Configure logging based on environment
configure_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="EcoCode Orchestrator", 
    version=__version__,
    description="Spec-driven development orchestration service",
    docs_url="/docs" if os.getenv("ECOCODE_ENABLE_DOCS", "true").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("ECOCODE_ENABLE_DOCS", "true").lower() == "true" else None,
)

# Add production middleware if enabled
if os.getenv("ECOCODE_ENABLE_CORS", "false").lower() == "true":
    from fastapi.middleware.cors import CORSMiddleware
    
    allowed_origins = os.getenv("ECOCODE_ALLOWED_ORIGINS", "").split(",")
    allowed_origins = [origin.strip() for origin in allowed_origins if origin.strip()]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Add HSTS header if HTTPS is enforced
    if os.getenv("ECOCODE_ENFORCE_HTTPS", "false").lower() == "true":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# Include routers
app.include_router(specs_router)

# Include security dashboard router
from eco_api.security import security_dashboard_router
app.include_router(security_dashboard_router)


@app.on_event("startup")
async def startup_event():
    """Initialize security system on application startup."""
    try:
        # Get workspace root from settings
        settings = get_settings()
        workspace_root = str(settings.workspace_root)
        
        # Initialize security system
        success = await quick_setup_security(workspace_root)
        if success:
            logger.info("Security system initialized successfully")
        else:
            logger.error("Failed to initialize security system")
    except Exception as e:
        logger.error(f"Error initializing security system: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown security system gracefully."""
    try:
        from eco_api.security.security_init import shutdown_security_system
        await shutdown_security_system()
        logger.info("Security system shutdown completed")
    except Exception as e:
        logger.error(f"Error shutting down security system: {e}")


SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_workspace_manager(settings: SettingsDep) -> WorkspaceManager:
    return WorkspaceManager(settings=settings)


WorkspaceManagerDep = Annotated[WorkspaceManager, Depends(get_workspace_manager)]


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__, timestamp=datetime.now(UTC))


@app.get("/health/detailed")
def detailed_health(settings: SettingsDep) -> dict:
    """Detailed health check for production monitoring."""
    try:
        # Import here to avoid circular imports
        from eco_api.specs.performance import get_cache_stats
        
        # Basic health info
        health_info = {
            "status": "healthy",
            "version": __version__,
            "timestamp": datetime.now(UTC).isoformat(),
            "environment": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "specs_enabled": settings.specs.enabled,
                "aws_bedrock_enabled": settings.aws.use_bedrock,
                "aws_s3_enabled": settings.aws.use_s3_sync,
            },
            "configuration": {
                "max_concurrent_specs": settings.specs.max_concurrent_tasks,
                "task_timeout_minutes": settings.specs.task_timeout_minutes,
                "auto_backup": settings.specs.auto_backup,
                "research_integration": settings.specs.enable_research_integration,
            },
            "performance": get_cache_stats(),
        }
        
        # Add system info if available
        try:
            import psutil
            process = psutil.Process()
            health_info["system"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "process_memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "open_files": len(process.open_files()),
                "num_threads": process.num_threads(),
            }
        except ImportError:
            health_info["system"] = {"error": "psutil not available"}
        
        return health_info
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(UTC).isoformat(),
        }


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
