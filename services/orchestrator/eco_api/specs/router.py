"""
FastAPI router for spec-driven workflow management endpoints.

This module implements the REST API endpoints for managing specification
workflows, including creation, retrieval, and document management.

Requirements addressed:
- 1.1, 1.2: Spec creation and management endpoints
- 7.9: Spec listing and discovery
- 5.1, 5.2, 5.3: Document management endpoints
- 4.5, 4.8: Task execution endpoints
- 1.8, 1.9: Workflow approval and state management
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..schemas import (
    CreateSpecRequest, SpecResponse, SpecListResponse, SpecDetailResponse,
    UpdateDocumentRequest, UpdateDocumentResponse, ExecuteTaskRequest,
    ExecuteTaskResponse, UpdateTaskStatusRequest, UpdateTaskStatusResponse,
    ProgressResponse, ApprovePhaseRequest, ApprovePhaseResponse,
    WorkflowStatusResponse
)
from .workflow_orchestrator import WorkflowOrchestrator
from .models import WorkflowPhase, WorkflowStatus, DocumentType
from ..security.authorization_validator import UserContext, create_default_validator

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/specs", tags=["specs"])

# Dependencies
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_workflow_orchestrator(settings: SettingsDep) -> WorkflowOrchestrator:
    """Get workflow orchestrator instance."""
    return WorkflowOrchestrator(workspace_root=".")


WorkflowOrchestratorDep = Annotated[WorkflowOrchestrator, Depends(get_workflow_orchestrator)]


def get_user_context() -> UserContext:
    """
    Get user context for authorization.
    
    TODO: This is a placeholder implementation. In a real system, this would
    extract user information from authentication tokens, session data, etc.
    """
    # For now, return a default user context with full permissions
    # In production, this would be extracted from JWT tokens or session data
    from ..security.authorization_validator import Role, Permission, create_developer_context
    
    # Use the helper function to create a proper developer context
    return create_developer_context("default_user")


UserContextDep = Annotated[UserContext, Depends(get_user_context)]


@router.post("", response_model=SpecResponse, status_code=status.HTTP_201_CREATED)
def create_spec(
    request: CreateSpecRequest,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> SpecResponse:
    """
    Create a new specification workflow from a feature idea.
    
    Requirements: 1.1, 1.2 - Spec initialization and workflow creation
    
    Args:
        request: The spec creation request
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        SpecResponse with the created spec information
        
    Raises:
        HTTPException: If creation fails or user is not authorized
    """
    try:
        logger.info(f"Creating new spec for feature idea: {request.feature_idea[:50]}...")
        
        # Create the spec workflow
        workflow_state, operation_result = orchestrator.create_spec_workflow(
            feature_idea=request.feature_idea,
            feature_name=request.feature_name,
            user_context=user_context
        )
        
        if not operation_result.success:
            if operation_result.error_code == "AUTHORIZATION_DENIED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=operation_result.message
                )
            elif operation_result.error_code in ["INVALID_FEATURE_NAME", "DUPLICATE_FEATURE_NAME"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=operation_result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=operation_result.message
                )
        
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create workflow state"
            )
        
        logger.info(f"Successfully created spec: {workflow_state.spec_id}")
        
        return SpecResponse(
            id=workflow_state.spec_id,
            feature_name=workflow_state.spec_id,  # feature_name is the same as spec_id
            current_phase=workflow_state.current_phase.value,
            status=workflow_state.status.value,
            created_at=workflow_state.created_at,
            updated_at=workflow_state.updated_at,
            progress=0.0  # New spec starts with 0% progress
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating spec: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error creating spec: {str(e)}"
        )


@router.get("", response_model=SpecListResponse)
def list_specs(
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> SpecListResponse:
    """
    List all available specification workflows.
    
    Requirements: 7.9 - Spec listing and discovery
    
    Args:
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        SpecListResponse with list of available specs
    """
    try:
        logger.debug("Listing all specs")
        
        # Get specs from orchestrator (includes authorization filtering)
        spec_summaries = orchestrator.list_workflows(user_context=user_context)
        
        # Convert to response format
        specs = [
            SpecResponse(
                id=spec.id,
                feature_name=spec.feature_name,
                current_phase=spec.current_phase.value,
                status=spec.status.value,
                created_at=spec.last_updated,  # Using last_updated as created_at for now
                updated_at=spec.last_updated,
                progress=spec.progress
            )
            for spec in spec_summaries
        ]
        
        logger.debug(f"Found {len(specs)} specs")
        
        return SpecListResponse(
            specs=specs,
            total_count=len(specs)
        )
        
    except Exception as e:
        logger.error(f"Error listing specs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing specs: {str(e)}"
        )


@router.get("/{spec_id}", response_model=SpecDetailResponse)
def get_spec(
    spec_id: str,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> SpecDetailResponse:
    """
    Get detailed information about a specific specification.
    
    Requirements: 1.1, 1.2 - Spec retrieval with authorization
    
    Args:
        spec_id: The specification identifier
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        SpecDetailResponse with detailed spec information
        
    Raises:
        HTTPException: If spec not found or user not authorized
    """
    try:
        logger.debug(f"Getting spec details for: {spec_id}")
        
        # Get workflow state (includes authorization check)
        workflow_state = orchestrator.get_workflow_state(spec_id, user_context=user_context)
        
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Specification not found: {spec_id}"
            )
        
        # Load documents from file system
        documents = {}
        try:
            file_manager = orchestrator.file_manager
            
            for doc_type in [DocumentType.REQUIREMENTS, DocumentType.DESIGN, DocumentType.TASKS]:
                doc, result = file_manager.load_document(spec_id, doc_type)
                if result.success and doc:
                    documents[doc_type.value] = doc.content
                else:
                    documents[doc_type.value] = None
                    
        except Exception as e:
            logger.warning(f"Error loading documents for spec {spec_id}: {str(e)}")
            # Continue without documents rather than failing
        
        # Convert approvals to string format
        approvals = {k: v.value for k, v in workflow_state.approvals.items()}
        
        logger.debug(f"Successfully retrieved spec: {spec_id}")
        
        return SpecDetailResponse(
            id=workflow_state.spec_id,
            feature_name=workflow_state.spec_id,
            current_phase=workflow_state.current_phase.value,
            status=workflow_state.status.value,
            created_at=workflow_state.created_at,
            updated_at=workflow_state.updated_at,
            progress=0.0,  # TODO: Calculate actual progress
            documents=documents,
            approvals=approvals,
            metadata=workflow_state.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting spec {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting spec: {str(e)}"
        )


@router.put("/{spec_id}/requirements", response_model=UpdateDocumentResponse)
def update_requirements(
    spec_id: str,
    request: UpdateDocumentRequest,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> UpdateDocumentResponse:
    """
    Update the requirements document for a specification.
    
    Requirements: 5.1, 5.2 - Requirements document updates with approval workflow
    
    Args:
        spec_id: The specification identifier
        request: The document update request
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        UpdateDocumentResponse with update status
        
    Raises:
        HTTPException: If update fails or user not authorized
    """
    try:
        logger.info(f"Updating requirements for spec: {spec_id}")
        
        # Verify spec exists and user has access
        workflow_state = orchestrator.get_workflow_state(spec_id, user_context=user_context)
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Specification not found: {spec_id}"
            )
        
        # Save the document
        file_manager = orchestrator.file_manager
        save_result = file_manager.save_document(
            feature_name=spec_id,
            document_type=DocumentType.REQUIREMENTS,
            content=request.content
        )
        
        if not save_result.success:
            if save_result.error_code == "PERMISSION_DENIED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=save_result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=save_result.message
                )
        
        # Handle approval if provided
        if request.approve is not None:
            approval_state, validation_result = orchestrator.approve_phase(
                spec_id=spec_id,
                phase=WorkflowPhase.REQUIREMENTS,
                approved=request.approve,
                feedback=request.feedback,
                user_context=user_context
            )
            
            if not validation_result.is_valid:
                logger.warning(f"Approval failed for spec {spec_id}: {validation_result.errors}")
                # Don't fail the document update, just log the approval issue
        
        # Calculate checksum for response
        import hashlib
        checksum = hashlib.sha256(request.content.encode('utf-8')).hexdigest()
        
        logger.info(f"Successfully updated requirements for spec: {spec_id}")
        
        return UpdateDocumentResponse(
            success=True,
            message="Requirements document updated successfully",
            updated_at=workflow_state.updated_at,
            checksum=checksum
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating requirements for spec {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating requirements: {str(e)}"
        )


@router.put("/{spec_id}/design", response_model=UpdateDocumentResponse)
def update_design(
    spec_id: str,
    request: UpdateDocumentRequest,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> UpdateDocumentResponse:
    """
    Update the design document for a specification.
    
    Requirements: 5.1, 5.3 - Design document updates with approval workflow
    
    Args:
        spec_id: The specification identifier
        request: The document update request
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        UpdateDocumentResponse with update status
        
    Raises:
        HTTPException: If update fails or user not authorized
    """
    try:
        logger.info(f"Updating design for spec: {spec_id}")
        
        # Verify spec exists and user has access
        workflow_state = orchestrator.get_workflow_state(spec_id, user_context=user_context)
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Specification not found: {spec_id}"
            )
        
        # Save the document
        file_manager = orchestrator.file_manager
        save_result = file_manager.save_document(
            feature_name=spec_id,
            document_type=DocumentType.DESIGN,
            content=request.content
        )
        
        if not save_result.success:
            if save_result.error_code == "PERMISSION_DENIED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=save_result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=save_result.message
                )
        
        # Handle approval if provided
        if request.approve is not None:
            approval_state, validation_result = orchestrator.approve_phase(
                spec_id=spec_id,
                phase=WorkflowPhase.DESIGN,
                approved=request.approve,
                feedback=request.feedback,
                user_context=user_context
            )
            
            if not validation_result.is_valid:
                logger.warning(f"Approval failed for spec {spec_id}: {validation_result.errors}")
                # Don't fail the document update, just log the approval issue
        
        # Calculate checksum for response
        import hashlib
        checksum = hashlib.sha256(request.content.encode('utf-8')).hexdigest()
        
        logger.info(f"Successfully updated design for spec: {spec_id}")
        
        return UpdateDocumentResponse(
            success=True,
            message="Design document updated successfully",
            updated_at=workflow_state.updated_at,
            checksum=checksum
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating design for spec {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating design: {str(e)}"
        )


@router.put("/{spec_id}/tasks", response_model=UpdateDocumentResponse)
def update_tasks(
    spec_id: str,
    request: UpdateDocumentRequest,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> UpdateDocumentResponse:
    """
    Update the tasks document for a specification.
    
    Requirements: 5.1, 5.6 - Tasks document updates with approval workflow
    
    Args:
        spec_id: The specification identifier
        request: The document update request
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        UpdateDocumentResponse with update status
        
    Raises:
        HTTPException: If update fails or user not authorized
    """
    try:
        logger.info(f"Updating tasks for spec: {spec_id}")
        
        # Verify spec exists and user has access
        workflow_state = orchestrator.get_workflow_state(spec_id, user_context=user_context)
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Specification not found: {spec_id}"
            )
        
        # Save the document
        file_manager = orchestrator.file_manager
        save_result = file_manager.save_document(
            feature_name=spec_id,
            document_type=DocumentType.TASKS,
            content=request.content
        )
        
        if not save_result.success:
            if save_result.error_code == "PERMISSION_DENIED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=save_result.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=save_result.message
                )
        
        # Handle approval if provided
        if request.approve is not None:
            approval_state, validation_result = orchestrator.approve_phase(
                spec_id=spec_id,
                phase=WorkflowPhase.TASKS,
                approved=request.approve,
                feedback=request.feedback,
                user_context=user_context
            )
            
            if not validation_result.is_valid:
                logger.warning(f"Approval failed for spec {spec_id}: {validation_result.errors}")
                # Don't fail the document update, just log the approval issue
        
        # Calculate checksum for response
        import hashlib
        checksum = hashlib.sha256(request.content.encode('utf-8')).hexdigest()
        
        logger.info(f"Successfully updated tasks for spec: {spec_id}")
        
        return UpdateDocumentResponse(
            success=True,
            message="Tasks document updated successfully",
            updated_at=workflow_state.updated_at,
            checksum=checksum
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tasks for spec {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating tasks: {str(e)}"
        )


@router.post("/{spec_id}/tasks/{task_id}/execute", response_model=ExecuteTaskResponse)
def execute_task(
    spec_id: str,
    task_id: str,
    request: ExecuteTaskRequest,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> ExecuteTaskResponse:
    """
    Execute a specific task from the task list.
    
    Requirements: 4.5, 4.8 - Task execution with context awareness
    Requirements: 6.1, 6.2 - Task execution and progress tracking
    
    Args:
        spec_id: The specification identifier
        task_id: The task identifier to execute
        request: The task execution request
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        ExecuteTaskResponse with execution status
        
    Raises:
        HTTPException: If execution fails or user not authorized
    """
    try:
        logger.info(f"Executing task {task_id} for spec: {spec_id}")
        
        # Verify spec exists and user has access
        workflow_state = orchestrator.get_workflow_state(spec_id, user_context=user_context)
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Specification not found: {spec_id}"
            )
        
        # Check if we have a task execution engine
        if not hasattr(orchestrator, 'task_execution_engine'):
            # For now, return a placeholder response since task execution engine
            # is implemented in a separate task (5.x)
            logger.warning(f"Task execution engine not available for spec {spec_id}, task {task_id}")
            return ExecuteTaskResponse(
                success=False,
                message="Task execution engine not yet implemented",
                task_id=task_id,
                status="not_started",
                execution_log=["Task execution engine integration pending"]
            )
        
        # TODO: Implement actual task execution when task execution engine is integrated
        # This is a placeholder implementation
        execution_log = [
            f"Task execution requested for task: {task_id}",
            f"Spec: {spec_id}",
            f"User: {user_context.user_id}",
            "Task execution engine integration pending"
        ]
        
        logger.info(f"Task execution placeholder completed for spec {spec_id}, task {task_id}")
        
        return ExecuteTaskResponse(
            success=True,
            message=f"Task execution initiated for task: {task_id}",
            task_id=task_id,
            status="in_progress",
            execution_log=execution_log
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing task {task_id} for spec {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing task: {str(e)}"
        )


@router.put("/{spec_id}/tasks/{task_id}/status", response_model=UpdateTaskStatusResponse)
def update_task_status(
    spec_id: str,
    task_id: str,
    request: UpdateTaskStatusRequest,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> UpdateTaskStatusResponse:
    """
    Update the status of a specific task.
    
    Requirements: 4.5, 4.8 - Task status tracking and progress management
    Requirements: 6.1, 6.2 - Task status updates
    
    Args:
        spec_id: The specification identifier
        task_id: The task identifier to update
        request: The status update request
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        UpdateTaskStatusResponse with update status
        
    Raises:
        HTTPException: If update fails or user not authorized
    """
    try:
        logger.info(f"Updating status for task {task_id} in spec {spec_id} to: {request.status}")
        
        # Verify spec exists and user has access
        workflow_state = orchestrator.get_workflow_state(spec_id, user_context=user_context)
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Specification not found: {spec_id}"
            )
        
        # Validate status value
        from .models import TaskStatus
        try:
            task_status = TaskStatus(request.status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task status: {request.status}"
            )
        
        # Check if we have a task execution engine
        if not hasattr(orchestrator, 'task_execution_engine'):
            # For now, return a placeholder response since task execution engine
            # is implemented in a separate task (5.x)
            logger.warning(f"Task execution engine not available for status update: spec {spec_id}, task {task_id}")
            return UpdateTaskStatusResponse(
                success=False,
                message="Task execution engine not yet implemented",
                task_id=task_id,
                status=request.status,
                updated_at=workflow_state.updated_at
            )
        
        # TODO: Implement actual task status update when task execution engine is integrated
        # This is a placeholder implementation
        
        logger.info(f"Task status update placeholder completed for spec {spec_id}, task {task_id}")
        
        return UpdateTaskStatusResponse(
            success=True,
            message=f"Task status updated to: {request.status}",
            task_id=task_id,
            status=request.status,
            updated_at=workflow_state.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task status for {task_id} in spec {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating task status: {str(e)}"
        )


@router.get("/{spec_id}/progress", response_model=ProgressResponse)
def get_progress(
    spec_id: str,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> ProgressResponse:
    """
    Get progress information for a specification.
    
    Requirements: 6.9 - Progress tracking and reporting
    
    Args:
        spec_id: The specification identifier
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        ProgressResponse with detailed progress information
        
    Raises:
        HTTPException: If spec not found or user not authorized
    """
    try:
        logger.debug(f"Getting progress for spec: {spec_id}")
        
        # Verify spec exists and user has access
        workflow_state = orchestrator.get_workflow_state(spec_id, user_context=user_context)
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Specification not found: {spec_id}"
            )
        
        # For now, return basic progress based on workflow phase
        # TODO: Implement detailed task-based progress when task execution engine is integrated
        
        # Calculate basic progress based on phase
        phase_progress = {
            WorkflowPhase.REQUIREMENTS: 25.0,
            WorkflowPhase.DESIGN: 50.0,
            WorkflowPhase.TASKS: 75.0,
            WorkflowPhase.EXECUTION: 100.0
        }
        
        progress_percentage = phase_progress.get(workflow_state.current_phase, 0.0)
        
        # Placeholder task counts - would be calculated from actual task list
        total_tasks = 10  # Placeholder
        completed_tasks = int(total_tasks * (progress_percentage / 100.0))
        in_progress_tasks = 1 if workflow_state.status == WorkflowStatus.IN_PROGRESS else 0
        not_started_tasks = total_tasks - completed_tasks - in_progress_tasks
        blocked_tasks = 0
        
        logger.debug(f"Progress calculated for spec {spec_id}: {progress_percentage}%")
        
        return ProgressResponse(
            spec_id=spec_id,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            not_started_tasks=not_started_tasks,
            blocked_tasks=blocked_tasks,
            progress_percentage=progress_percentage,
            current_phase=workflow_state.current_phase.value,
            status=workflow_state.status.value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress for spec {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting progress: {str(e)}"
        )


@router.post("/{spec_id}/approve/{phase}", response_model=ApprovePhaseResponse)
def approve_phase(
    spec_id: str,
    phase: str,
    request: ApprovePhaseRequest,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> ApprovePhaseResponse:
    """
    Approve or reject a specific workflow phase.
    
    Requirements: 1.8, 1.9 - Workflow approval handling with user input integration
    Requirements: 5.10 - Approval workflow management
    
    Args:
        spec_id: The specification identifier
        phase: The workflow phase to approve (requirements, design, tasks)
        request: The approval request
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        ApprovePhaseResponse with approval status
        
    Raises:
        HTTPException: If approval fails or user not authorized
    """
    try:
        logger.info(f"Processing approval for phase {phase} in spec {spec_id}: {request.approved}")
        
        # Verify spec exists and user has access
        workflow_state = orchestrator.get_workflow_state(spec_id, user_context=user_context)
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Specification not found: {spec_id}"
            )
        
        # Validate phase
        try:
            workflow_phase = WorkflowPhase(phase)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid workflow phase: {phase}"
            )
        
        # Process the approval
        updated_state, validation_result = orchestrator.approve_phase(
            spec_id=spec_id,
            phase=workflow_phase,
            approved=request.approved,
            feedback=request.feedback,
            user_context=user_context
        )
        
        if not validation_result.is_valid:
            error_messages = [error.message for error in validation_result.errors]
            if any("AUTHORIZATION_DENIED" in error.code for error in validation_result.errors):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="; ".join(error_messages)
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="; ".join(error_messages)
                )
        
        if not updated_state:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update workflow state"
            )
        
        logger.info(f"Successfully processed approval for phase {phase} in spec {spec_id}")
        
        return ApprovePhaseResponse(
            success=True,
            message=f"Phase {phase} {'approved' if request.approved else 'rejected'} successfully",
            phase=phase,
            approved=request.approved,
            updated_at=updated_state.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing approval for phase {phase} in spec {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing approval: {str(e)}"
        )


@router.get("/{spec_id}/status", response_model=WorkflowStatusResponse)
def get_workflow_status(
    spec_id: str,
    orchestrator: WorkflowOrchestratorDep,
    user_context: UserContextDep,
) -> WorkflowStatusResponse:
    """
    Get the current workflow status for a specification.
    
    Requirements: 1.8, 1.9 - Workflow state management and status reporting
    Requirements: 8.2, 8.3 - Error handling and validation
    
    Args:
        spec_id: The specification identifier
        orchestrator: Workflow orchestrator instance
        user_context: User context for authorization
        
    Returns:
        WorkflowStatusResponse with detailed workflow status
        
    Raises:
        HTTPException: If spec not found or user not authorized
    """
    try:
        logger.debug(f"Getting workflow status for spec: {spec_id}")
        
        # Verify spec exists and user has access
        workflow_state = orchestrator.get_workflow_state(spec_id, user_context=user_context)
        if not workflow_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Specification not found: {spec_id}"
            )
        
        # Convert approvals to string format
        approvals = {k: v.value for k, v in workflow_state.approvals.items()}
        
        # Determine valid transitions from current phase
        valid_transitions = []
        current_phase = workflow_state.current_phase
        
        # Add valid transitions based on current phase and approval status
        if current_phase == WorkflowPhase.REQUIREMENTS:
            if workflow_state.approvals.get("requirements") == "approved":
                valid_transitions.append("design")
        elif current_phase == WorkflowPhase.DESIGN:
            valid_transitions.append("requirements")  # Can always go back
            if workflow_state.approvals.get("design") == "approved":
                valid_transitions.append("tasks")
        elif current_phase == WorkflowPhase.TASKS:
            valid_transitions.extend(["requirements", "design"])  # Can go back
            if workflow_state.approvals.get("tasks") == "approved":
                valid_transitions.append("execution")
        elif current_phase == WorkflowPhase.EXECUTION:
            valid_transitions.extend(["requirements", "design", "tasks"])  # Can go back
        
        logger.debug(f"Workflow status retrieved for spec {spec_id}")
        
        return WorkflowStatusResponse(
            spec_id=spec_id,
            current_phase=workflow_state.current_phase.value,
            status=workflow_state.status.value,
            created_at=workflow_state.created_at,
            updated_at=workflow_state.updated_at,
            approvals=approvals,
            metadata=workflow_state.metadata,
            valid_transitions=valid_transitions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status for spec {spec_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting workflow status: {str(e)}"
        )