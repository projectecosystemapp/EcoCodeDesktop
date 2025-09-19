"""
Workflow orchestrator for spec-driven development process.

This module implements the core workflow orchestration logic, managing
state transitions, approval workflows, and coordination between different
phases of the spec-driven development process.

Requirements addressed:
- 1.8, 1.9, 1.10, 1.11: Workflow state transitions and approval handling
- 8.1, 8.7: Workflow state management and validation
"""

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from uuid import uuid4

from .models import (
    WorkflowPhase, WorkflowStatus, TaskStatus, DocumentType,
    SpecMetadata, ValidationResult, ValidationError, ValidationWarning,
    FileOperationResult, SpecSummary
)
from .file_manager import FileSystemManager
from .workflow_persistence import WorkflowPersistenceManager
from .workflow_validation import WorkflowValidator, WorkflowErrorHandler
from ..security.authorization_validator import (
    AuthorizationValidator, UserContext, Permission, Role,
    create_default_validator
)


logger = logging.getLogger(__name__)


class WorkflowTransitionType(str, Enum):
    """Types of workflow transitions."""
    FORWARD = "forward"
    BACKWARD = "backward"
    LATERAL = "lateral"


class ApprovalStatus(str, Enum):
    """Status of approval for workflow phases."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class WorkflowTransition:
    """Defines a valid workflow transition."""
    
    def __init__(
        self,
        from_phase: WorkflowPhase,
        to_phase: WorkflowPhase,
        transition_type: WorkflowTransitionType,
        requires_approval: bool = False,
        validation_rules: Optional[List[str]] = None
    ):
        self.from_phase = from_phase
        self.to_phase = to_phase
        self.transition_type = transition_type
        self.requires_approval = requires_approval
        self.validation_rules = validation_rules or []


class WorkflowState:
    """Represents the current state of a workflow."""
    
    def __init__(
        self,
        spec_id: str,
        current_phase: WorkflowPhase,
        status: WorkflowStatus,
        approvals: Optional[Dict[str, ApprovalStatus]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.spec_id = spec_id
        self.current_phase = current_phase
        self.status = status
        self.approvals = approvals or {}
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow state to dictionary for serialization."""
        return {
            "spec_id": self.spec_id,
            "current_phase": self.current_phase.value,
            "status": self.status.value,
            "approvals": {k: v.value for k, v in self.approvals.items()},
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowState':
        """Create workflow state from dictionary."""
        state = cls(
            spec_id=data["spec_id"],
            current_phase=WorkflowPhase(data["current_phase"]),
            status=WorkflowStatus(data["status"]),
            approvals={k: ApprovalStatus(v) for k, v in data.get("approvals", {}).items()},
            metadata=data.get("metadata", {})
        )
        
        if "created_at" in data:
            state.created_at = datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            state.updated_at = datetime.fromisoformat(data["updated_at"])
        
        return state


class WorkflowOrchestrator:
    """
    Core workflow orchestrator for spec-driven development.
    
    Manages workflow state transitions, approval processes, and coordination
    between different phases of the development process.
    
    Requirements: 1.8, 1.9, 1.10, 1.11, 8.1, 8.7
    """
    
    # Define valid workflow transitions
    VALID_TRANSITIONS = [
        # Forward transitions (require approval)
        WorkflowTransition(
            WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN,
            WorkflowTransitionType.FORWARD, requires_approval=True,
            validation_rules=["requirements_complete", "requirements_approved"]
        ),
        WorkflowTransition(
            WorkflowPhase.DESIGN, WorkflowPhase.TASKS,
            WorkflowTransitionType.FORWARD, requires_approval=True,
            validation_rules=["design_complete", "design_approved"]
        ),
        WorkflowTransition(
            WorkflowPhase.TASKS, WorkflowPhase.EXECUTION,
            WorkflowTransitionType.FORWARD, requires_approval=True,
            validation_rules=["tasks_complete", "tasks_approved"]
        ),
        
        # Backward transitions (no approval required)
        WorkflowTransition(
            WorkflowPhase.DESIGN, WorkflowPhase.REQUIREMENTS,
            WorkflowTransitionType.BACKWARD, requires_approval=False
        ),
        WorkflowTransition(
            WorkflowPhase.TASKS, WorkflowPhase.DESIGN,
            WorkflowTransitionType.BACKWARD, requires_approval=False
        ),
        WorkflowTransition(
            WorkflowPhase.TASKS, WorkflowPhase.REQUIREMENTS,
            WorkflowTransitionType.BACKWARD, requires_approval=False
        ),
        
        # Lateral transitions (within execution phase)
        WorkflowTransition(
            WorkflowPhase.EXECUTION, WorkflowPhase.EXECUTION,
            WorkflowTransitionType.LATERAL, requires_approval=False
        )
    ]
    
    def __init__(self, workspace_root: str = ".", authorization_validator: Optional[AuthorizationValidator] = None):
        """
        Initialize the workflow orchestrator.
        
        Args:
            workspace_root: Root directory of the workspace
            authorization_validator: Optional authorization validator (will create default if not provided)
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.file_manager = FileSystemManager(workspace_root)
        self.persistence_manager = WorkflowPersistenceManager(workspace_root)
        self.validator = WorkflowValidator()
        self.error_handler = WorkflowErrorHandler()
        self.workflow_states: Dict[str, WorkflowState] = {}
        
        # Initialize authorization validator
        self.auth_validator = authorization_validator or create_default_validator(workspace_root)
        
        self._load_existing_workflows()
    
    def create_spec_workflow(
        self, 
        feature_idea: str, 
        feature_name: Optional[str] = None,
        user_context: Optional[UserContext] = None
    ) -> Tuple[WorkflowState, FileOperationResult]:
        """
        Create a new spec workflow from a feature idea.
        
        Requirements: 1.1, 1.2 - Spec initialization and workflow creation
        Requirements: 4.1, 4.2 - Server-side authorization validation
        
        Args:
            feature_idea: The rough feature idea
            feature_name: Optional explicit feature name (will be generated if not provided)
            user_context: User context for authorization validation
            
        Returns:
            Tuple of (WorkflowState, FileOperationResult)
        """
        try:
            # Validate authorization for spec creation
            if user_context:
                auth_result = self.auth_validator.validate_server_side_permissions(
                    user_context=user_context,
                    operation="create_spec_workflow",
                    permission=Permission.SPEC_CREATE,
                    resource=feature_name
                )
                
                if not auth_result.authorized:
                    logger.warning(f"Unauthorized spec creation attempt by user {user_context.user_id}: {auth_result.reason}")
                    return None, FileOperationResult(
                        success=False,
                        message=f"Access denied: {auth_result.reason}",
                        error_code="AUTHORIZATION_DENIED"
                    )
                
                logger.info(f"Authorized spec creation for user {user_context.user_id}")
            else:
                # Log security event for missing user context
                logger.warning("Spec creation attempted without user context - potential security issue")
                return None, FileOperationResult(
                    success=False,
                    message="Access denied: User context required for spec creation",
                    error_code="MISSING_USER_CONTEXT"
                )
            
            # Generate feature name if not provided
            if not feature_name:
                feature_name = self.file_manager.generate_feature_name(feature_idea)
            
            # Validate feature name
            validation = self.file_manager.validate_feature_name(feature_name)
            if not validation.is_valid:
                return None, FileOperationResult(
                    success=False,
                    message=f"Invalid feature name: {validation.errors[0].message}",
                    error_code="INVALID_FEATURE_NAME"
                )
            
            # Check uniqueness
            uniqueness = self.file_manager.check_feature_name_uniqueness(feature_name)
            if not uniqueness.is_valid:
                return None, FileOperationResult(
                    success=False,
                    message=f"Feature name not unique: {uniqueness.errors[0].message}",
                    error_code="DUPLICATE_FEATURE_NAME"
                )
            
            # Create spec directory
            dir_result = self.file_manager.create_spec_directory(feature_name)
            if not dir_result.success:
                return None, dir_result
            
            # Create initial workflow state
            workflow_state = WorkflowState(
                spec_id=feature_name,
                current_phase=WorkflowPhase.REQUIREMENTS,
                status=WorkflowStatus.DRAFT,
                approvals={
                    "requirements": ApprovalStatus.PENDING,
                    "design": ApprovalStatus.PENDING,
                    "tasks": ApprovalStatus.PENDING
                },
                metadata={
                    "feature_idea": feature_idea,
                    "created_by": user_context.user_id if user_context else "system",
                    "created_by_roles": [role.value for role in user_context.roles] if user_context else [],
                    "version": "1.0.0"
                }
            )
            
            # Store workflow state
            self.workflow_states[feature_name] = workflow_state
            
            # Persist workflow state
            persist_result = self.persistence_manager.save_workflow_state(
                workflow_state, 
                create_version=True, 
                description="Initial workflow creation"
            )
            if not persist_result.success:
                # Cleanup on failure
                del self.workflow_states[feature_name]
                return None, persist_result
            
            logger.info(f"Created new spec workflow: {feature_name}")
            
            return workflow_state, FileOperationResult(
                success=True,
                message=f"Successfully created spec workflow: {feature_name}",
                path=dir_result.path
            )
            
        except Exception as e:
            logger.error(f"Error creating spec workflow: {str(e)}")
            return None, FileOperationResult(
                success=False,
                message=f"Unexpected error creating workflow: {str(e)}",
                error_code="UNKNOWN_ERROR"
            )
    
    def get_workflow_state(self, spec_id: str, user_context: Optional[UserContext] = None) -> Optional[WorkflowState]:
        """
        Get the current workflow state for a spec.
        
        Requirements: 4.1, 4.2 - Server-side authorization validation
        
        Args:
            spec_id: The spec identifier
            user_context: User context for authorization validation
            
        Returns:
            WorkflowState if found and authorized, None otherwise
        """
        # Validate authorization for reading workflow state
        if user_context:
            auth_result = self.auth_validator.validate_server_side_permissions(
                user_context=user_context,
                operation="get_workflow_state",
                permission=Permission.SPEC_READ,
                resource=spec_id
            )
            
            if not auth_result.authorized:
                logger.warning(f"Unauthorized workflow state access attempt by user {user_context.user_id}: {auth_result.reason}")
                return None
            
            logger.debug(f"Authorized workflow state access for user {user_context.user_id} on spec {spec_id}")
        else:
            # For backward compatibility, allow access without user context but log it
            logger.warning(f"Workflow state accessed without user context for spec {spec_id} - consider adding authorization")
        
        return self.workflow_states.get(spec_id)
    
    def transition_workflow(
        self,
        spec_id: str,
        target_phase: WorkflowPhase,
        approval: Optional[bool] = None,
        feedback: Optional[str] = None,
        user_context: Optional[UserContext] = None
    ) -> Tuple[Optional[WorkflowState], ValidationResult]:
        """
        Transition a workflow to a new phase with validation.
        
        Requirements: 1.8, 1.9 - Workflow state transitions and validation
        Requirements: 4.1, 4.2 - Server-side authorization validation
        
        Args:
            spec_id: The spec identifier
            target_phase: The target workflow phase
            approval: Whether the current phase is approved (for forward transitions)
            feedback: Optional feedback for the transition
            user_context: User context for authorization validation
            
        Returns:
            Tuple of (updated WorkflowState or None, ValidationResult)
        """
        try:
            # Validate authorization for workflow transition
            if user_context:
                auth_result = self.auth_validator.validate_server_side_permissions(
                    user_context=user_context,
                    operation="transition_workflow",
                    permission=Permission.WORKFLOW_TRANSITION,
                    resource=spec_id
                )
                
                if not auth_result.authorized:
                    logger.warning(f"Unauthorized workflow transition attempt by user {user_context.user_id}: {auth_result.reason}")
                    return None, ValidationResult(
                        is_valid=False,
                        errors=[ValidationError(
                            code="AUTHORIZATION_DENIED",
                            message=f"Access denied: {auth_result.reason}"
                        )]
                    )
                
                logger.info(f"Authorized workflow transition for user {user_context.user_id} on spec {spec_id}")
            else:
                # Log security event for missing user context
                logger.warning(f"Workflow transition attempted without user context for spec {spec_id} - potential security issue")
                return None, ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="MISSING_USER_CONTEXT",
                        message="Access denied: User context required for workflow transitions"
                    )]
                )
            
            # Get current workflow state
            current_state = self.workflow_states.get(spec_id)
            if not current_state:
                return None, ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="WORKFLOW_NOT_FOUND",
                        message=f"Workflow not found for spec: {spec_id}"
                    )]
                )
            
            # Validate transition
            validation = self._validate_transition(current_state, target_phase, approval)
            if not validation.is_valid:
                return None, validation
            
            # Get transition definition
            transition = self._get_transition(current_state.current_phase, target_phase)
            if not transition:
                return None, ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="INVALID_TRANSITION",
                        message=f"Invalid transition from {current_state.current_phase} to {target_phase}"
                    )]
                )
            
            # Handle approval for forward transitions
            if transition.requires_approval and approval is not None:
                phase_key = current_state.current_phase.value
                if approval:
                    current_state.approvals[phase_key] = ApprovalStatus.APPROVED
                else:
                    current_state.approvals[phase_key] = ApprovalStatus.NEEDS_REVISION
                    # Don't transition if not approved
                    current_state.updated_at = datetime.utcnow()
                    if feedback:
                        current_state.metadata[f"{phase_key}_feedback"] = feedback
                    
                    # Persist updated state
                    self.persistence_manager.save_workflow_state(
                        current_state,
                        create_version=False,
                        description="Approval feedback update"
                    )
                    
                    return current_state, ValidationResult(
                        is_valid=True,
                        warnings=[ValidationWarning(
                            code="APPROVAL_REQUIRED",
                            message=f"Phase {current_state.current_phase} requires approval before proceeding"
                        )]
                    )
            
            # Perform transition
            old_phase = current_state.current_phase
            current_state.current_phase = target_phase
            current_state.updated_at = datetime.utcnow()
            
            # Update status based on phase
            if target_phase == WorkflowPhase.EXECUTION:
                current_state.status = WorkflowStatus.IN_PROGRESS
            elif target_phase in [WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN, WorkflowPhase.TASKS]:
                current_state.status = WorkflowStatus.DRAFT
            
            # Add transition metadata with user information
            current_state.metadata[f"transition_{int(datetime.utcnow().timestamp())}"] = {
                "from": old_phase.value,
                "to": target_phase.value,
                "timestamp": datetime.utcnow().isoformat(),
                "feedback": feedback,
                "transitioned_by": user_context.user_id if user_context else "system",
                "user_roles": [role.value for role in user_context.roles] if user_context else []
            }
            
            # Persist updated state
            persist_result = self.persistence_manager.save_workflow_state(
                current_state,
                create_version=True,
                description=f"Transition from {old_phase} to {target_phase}"
            )
            if not persist_result.success:
                return None, ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="PERSISTENCE_ERROR",
                        message=f"Failed to persist workflow state: {persist_result.message}"
                    )]
                )
            
            logger.info(f"Transitioned workflow {spec_id} from {old_phase} to {target_phase}")
            
            return current_state, ValidationResult(is_valid=True)
            
        except Exception as e:
            logger.error(f"Error transitioning workflow {spec_id}: {str(e)}")
            return None, ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    code="TRANSITION_ERROR",
                    message=f"Unexpected error during transition: {str(e)}"
                )]
            )
    
    def approve_phase(
        self,
        spec_id: str,
        phase: WorkflowPhase,
        approved: bool,
        feedback: Optional[str] = None,
        user_context: Optional[UserContext] = None
    ) -> Tuple[Optional[WorkflowState], ValidationResult]:
        """
        Approve or reject a specific workflow phase.
        
        Requirements: 1.10, 1.11 - Approval workflow handling with user input integration
        Requirements: 4.1, 4.2 - Server-side authorization validation
        
        Args:
            spec_id: The spec identifier
            phase: The phase to approve/reject
            approved: Whether the phase is approved
            feedback: Optional feedback
            user_context: User context for authorization validation
            
        Returns:
            Tuple of (updated WorkflowState or None, ValidationResult)
        """
        try:
            # Validate authorization for phase approval
            if user_context:
                auth_result = self.auth_validator.validate_server_side_permissions(
                    user_context=user_context,
                    operation="approve_phase",
                    permission=Permission.WORKFLOW_APPROVE,
                    resource=f"{spec_id}:{phase.value}"
                )
                
                if not auth_result.authorized:
                    logger.warning(f"Unauthorized phase approval attempt by user {user_context.user_id}: {auth_result.reason}")
                    return None, ValidationResult(
                        is_valid=False,
                        errors=[ValidationError(
                            code="AUTHORIZATION_DENIED",
                            message=f"Access denied: {auth_result.reason}"
                        )]
                    )
                
                logger.info(f"Authorized phase approval for user {user_context.user_id} on spec {spec_id}, phase {phase}")
            else:
                # Log security event for missing user context
                logger.warning(f"Phase approval attempted without user context for spec {spec_id}, phase {phase} - potential security issue")
                return None, ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="MISSING_USER_CONTEXT",
                        message="Access denied: User context required for phase approvals"
                    )]
                )
            
            current_state = self.workflow_states.get(spec_id)
            if not current_state:
                return None, ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="WORKFLOW_NOT_FOUND",
                        message=f"Workflow not found for spec: {spec_id}"
                    )]
                )
            
            # Validate that we're approving the current phase
            if current_state.current_phase != phase:
                return None, ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="INVALID_PHASE_APPROVAL",
                        message=f"Cannot approve {phase} when current phase is {current_state.current_phase}"
                    )]
                )
            
            # Update approval status
            phase_key = phase.value
            current_state.approvals[phase_key] = ApprovalStatus.APPROVED if approved else ApprovalStatus.NEEDS_REVISION
            current_state.updated_at = datetime.utcnow()
            
            # Store feedback and approval metadata if provided
            if feedback:
                current_state.metadata[f"{phase_key}_feedback"] = feedback
                current_state.metadata[f"{phase_key}_feedback_timestamp"] = datetime.utcnow().isoformat()
            
            # Store approval metadata with user information
            current_state.metadata[f"{phase_key}_approved_by"] = user_context.user_id if user_context else "system"
            current_state.metadata[f"{phase_key}_approved_by_roles"] = [role.value for role in user_context.roles] if user_context else []
            current_state.metadata[f"{phase_key}_approval_timestamp"] = datetime.utcnow().isoformat()
            
            # Persist updated state
            persist_result = self.persistence_manager.save_workflow_state(
                current_state,
                create_version=True,
                description=f"Phase {phase} {'approved' if approved else 'rejected'}"
            )
            if not persist_result.success:
                return None, ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="PERSISTENCE_ERROR",
                        message=f"Failed to persist approval: {persist_result.message}"
                    )]
                )
            
            logger.info(f"Phase {phase} {'approved' if approved else 'rejected'} for spec {spec_id}")
            
            return current_state, ValidationResult(is_valid=True)
            
        except Exception as e:
            logger.error(f"Error approving phase {phase} for spec {spec_id}: {str(e)}")
            return None, ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    code="APPROVAL_ERROR",
                    message=f"Unexpected error during approval: {str(e)}"
                )]
            )
    
    def list_workflows(self, user_context: Optional[UserContext] = None) -> List[SpecSummary]:
        """
        List all available workflows.
        
        Requirements: 4.1, 4.2 - Server-side authorization validation
        
        Args:
            user_context: User context for authorization validation
        
        Returns:
            List of SpecSummary objects (filtered by user permissions)
        """
        try:
            # Validate authorization for listing workflows
            if user_context:
                auth_result = self.auth_validator.validate_server_side_permissions(
                    user_context=user_context,
                    operation="list_workflows",
                    permission=Permission.SPEC_READ,
                    resource="*"
                )
                
                if not auth_result.authorized:
                    logger.warning(f"Unauthorized workflow listing attempt by user {user_context.user_id}: {auth_result.reason}")
                    return []
                
                logger.debug(f"Authorized workflow listing for user {user_context.user_id}")
            else:
                # For backward compatibility, allow access without user context but log it
                logger.warning("Workflow listing accessed without user context - consider adding authorization")
            
            # Get specs from file system
            file_specs = self.file_manager.list_existing_specs()
            
            # Enhance with workflow state information
            enhanced_specs = []
            for spec in file_specs:
                workflow_state = self.workflow_states.get(spec.id)
                if workflow_state:
                    # Update with workflow information
                    spec.current_phase = workflow_state.current_phase
                    spec.status = workflow_state.status
                    spec.last_updated = workflow_state.updated_at
                
                enhanced_specs.append(spec)
            
            return enhanced_specs
            
        except Exception as e:
            logger.error(f"Error listing workflows: {str(e)}")
            return []
    
    def validate_workflow(self, spec_id: str) -> ValidationResult:
        """
        Validate the current state of a workflow using comprehensive validation.
        
        Requirements: 8.7 - Workflow validation and error handling
        
        Args:
            spec_id: The spec identifier
            
        Returns:
            ValidationResult with validation status
        """
        try:
            # Check if workflow exists
            workflow_state = self.workflow_states.get(spec_id)
            if not workflow_state:
                return ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="WORKFLOW_NOT_FOUND",
                        message=f"Workflow not found for spec: {spec_id}"
                    )]
                )
            
            # Use comprehensive validator
            validation_result = self.validator.validate_workflow_state(
                workflow_state=workflow_state,
                file_manager=self.file_manager
            )
            
            # Add file system validation
            structure_validation = self.file_manager.validate_spec_structure(spec_id)
            validation_result.errors.extend(structure_validation.errors)
            validation_result.warnings.extend(structure_validation.warnings)
            
            # Update validity based on all errors
            validation_result.is_valid = len(validation_result.errors) == 0
            
            return validation_result
            
        except Exception as e:
            # Use error handler for comprehensive error handling
            recovered, message, strategy = self.error_handler.handle_workflow_error(
                e, workflow_state, "validate_workflow"
            )
            
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    code="VALIDATION_ERROR",
                    message=f"Error validating workflow: {str(e)}"
                )]
            )
    
    def _validate_transition(
        self,
        current_state: WorkflowState,
        target_phase: WorkflowPhase,
        approval: Optional[bool]
    ) -> ValidationResult:
        """
        Validate a workflow transition using comprehensive validation.
        
        Args:
            current_state: Current workflow state
            target_phase: Target phase for transition
            approval: Approval status for current phase
            
        Returns:
            ValidationResult indicating if transition is valid
        """
        try:
            # Use comprehensive validator for transition validation
            validation_result = self.validator.validate_workflow_transition(
                workflow_state=current_state,
                target_phase=target_phase,
                file_manager=self.file_manager
            )
            
            # Additional approval validation
            transition = self._get_transition(current_state.current_phase, target_phase)
            if transition and transition.requires_approval:
                phase_key = current_state.current_phase.value
                current_approval = current_state.approvals.get(phase_key, ApprovalStatus.PENDING)
                
                if approval is None and current_approval != ApprovalStatus.APPROVED:
                    validation_result.errors.append(ValidationError(
                        code="APPROVAL_REQUIRED",
                        message=f"Phase {current_state.current_phase} requires approval before proceeding"
                    ))
                elif approval is True or current_approval == ApprovalStatus.APPROVED:
                    # Validate that required documents exist
                    validation_errors = self._validate_phase_requirements(
                        current_state.spec_id, current_state.current_phase
                    )
                    validation_result.errors.extend(validation_errors)
            
            # Update validity
            validation_result.is_valid = len(validation_result.errors) == 0
            
            return validation_result
            
        except Exception as e:
            # Use error handler
            recovered, message, strategy = self.error_handler.handle_workflow_error(
                e, current_state, "validate_transition"
            )
            
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    code="TRANSITION_VALIDATION_ERROR",
                    message=f"Error validating transition: {str(e)}"
                )]
            )
    
    def _validate_phase_requirements(self, spec_id: str, phase: WorkflowPhase) -> List[ValidationError]:
        """
        Validate that a phase has all required documents and content.
        
        Args:
            spec_id: The spec identifier
            phase: The phase to validate
            
        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []
        
        try:
            if phase == WorkflowPhase.REQUIREMENTS:
                req_doc, req_result = self.file_manager.load_document(spec_id, DocumentType.REQUIREMENTS)
                if not req_result.success or not req_doc or len(req_doc.content.strip()) == 0:
                    errors.append(ValidationError(
                        code="INCOMPLETE_REQUIREMENTS",
                        message="Requirements document must be complete before proceeding"
                    ))
            
            elif phase == WorkflowPhase.DESIGN:
                design_doc, design_result = self.file_manager.load_document(spec_id, DocumentType.DESIGN)
                if not design_result.success or not design_doc or len(design_doc.content.strip()) == 0:
                    errors.append(ValidationError(
                        code="INCOMPLETE_DESIGN",
                        message="Design document must be complete before proceeding"
                    ))
            
            elif phase == WorkflowPhase.TASKS:
                tasks_doc, tasks_result = self.file_manager.load_document(spec_id, DocumentType.TASKS)
                if not tasks_result.success or not tasks_doc or len(tasks_doc.content.strip()) == 0:
                    errors.append(ValidationError(
                        code="INCOMPLETE_TASKS",
                        message="Tasks document must be complete before proceeding"
                    ))
        
        except Exception as e:
            errors.append(ValidationError(
                code="VALIDATION_ERROR",
                message=f"Error validating phase requirements: {str(e)}"
            ))
        
        return errors
    
    def _get_transition(self, from_phase: WorkflowPhase, to_phase: WorkflowPhase) -> Optional[WorkflowTransition]:
        """
        Get the transition definition for a phase change.
        
        Args:
            from_phase: Source phase
            to_phase: Target phase
            
        Returns:
            WorkflowTransition if valid, None otherwise
        """
        for transition in self.VALID_TRANSITIONS:
            if transition.from_phase == from_phase and transition.to_phase == to_phase:
                return transition
        return None
    
    def _load_existing_workflows(self) -> None:
        """
        Load existing workflow states from disk using persistence manager.
        """
        try:
            specs_dir = self.workspace_root / self.file_manager.SPEC_BASE_PATH
            if not specs_dir.exists():
                return
            
            for spec_dir in specs_dir.iterdir():
                if not spec_dir.is_dir():
                    continue
                
                spec_id = spec_dir.name
                workflow_state, load_result = self.persistence_manager.load_workflow_state(spec_id)
                
                if load_result.success and workflow_state:
                    self.workflow_states[spec_id] = workflow_state
                    logger.debug(f"Loaded workflow state for {spec_id}")
                elif load_result.error_code in ["STATE_NOT_FOUND", "JSON_ERROR", "INTEGRITY_ERROR"]:
                    # Attempt recovery
                    recovered_state, recovery_result = self.persistence_manager.recover_workflow_state(spec_id)
                    if recovery_result.success and recovered_state:
                        self.workflow_states[spec_id] = recovered_state
                        logger.info(f"Recovered workflow state for {spec_id}: {recovery_result.message}")
                    else:
                        logger.warning(f"Failed to load or recover workflow state for {spec_id}: {load_result.message}")
                else:
                    logger.warning(f"Failed to load workflow state for {spec_id}: {load_result.message}")
        
        except Exception as e:
            logger.error(f"Error loading existing workflows: {str(e)}")
    
    def get_workflow_versions(self, spec_id: str) -> List[Any]:
        """
        Get available versions for a workflow.
        
        Requirements: 8.11 - Workflow metadata management and versioning
        
        Args:
            spec_id: The spec identifier
            
        Returns:
            List of available workflow versions
        """
        return self.persistence_manager.list_workflow_versions(spec_id)
    
    def restore_workflow_version(self, spec_id: str, version_id: str) -> Tuple[Optional[WorkflowState], ValidationResult]:
        """
        Restore a specific workflow version.
        
        Requirements: 8.10, 8.11 - Workflow recovery and versioning
        
        Args:
            spec_id: The spec identifier
            version_id: The version identifier to restore
            
        Returns:
            Tuple of (restored WorkflowState or None, ValidationResult)
        """
        try:
            restored_state, restore_result = self.persistence_manager.restore_workflow_version(spec_id, version_id)
            
            if restore_result.success and restored_state:
                # Update in-memory state
                self.workflow_states[spec_id] = restored_state
                
                return restored_state, ValidationResult(is_valid=True)
            else:
                return None, ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="RESTORE_FAILED",
                        message=restore_result.message
                    )]
                )
        
        except Exception as e:
            logger.error(f"Error restoring workflow version: {str(e)}")
            return None, ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    code="RESTORE_ERROR",
                    message=f"Unexpected error during restore: {str(e)}"
                )]
            )    

    def handle_workflow_error_with_recovery(
        self,
        spec_id: str,
        error: Exception,
        operation: str
    ) -> Tuple[bool, str, Optional[WorkflowState]]:
        """
        Handle workflow errors with automatic recovery attempts.
        
        Requirements: 8.2, 8.3 - Error recovery strategies for workflow failures
        
        Args:
            spec_id: The spec identifier
            error: The error that occurred
            operation: The operation that failed
            
        Returns:
            Tuple of (recovered, message, updated_workflow_state)
        """
        try:
            workflow_state = self.workflow_states.get(spec_id)
            
            # Use error handler for recovery
            recovered, message, strategy = self.error_handler.handle_workflow_error(
                error=error,
                workflow_state=workflow_state,
                operation=operation,
                context={
                    "file_manager": self.file_manager,
                    "persistence_manager": self.persistence_manager,
                    "orchestrator": self
                }
            )
            
            # If recovery was successful, reload workflow state
            updated_state = workflow_state
            if recovered and workflow_state:
                # Reload state from persistence
                reloaded_state, load_result = self.persistence_manager.load_workflow_state(spec_id)
                if load_result.success and reloaded_state:
                    self.workflow_states[spec_id] = reloaded_state
                    updated_state = reloaded_state
            
            logger.info(f"Error recovery for {spec_id}: recovered={recovered}, strategy={strategy}, message={message}")
            
            return recovered, message, updated_state
            
        except Exception as recovery_error:
            logger.error(f"Error during error recovery for {spec_id}: {str(recovery_error)}")
            return False, f"Recovery failed: {str(recovery_error)}", workflow_state
    
    def validate_and_recover_workflow(self, spec_id: str) -> Tuple[ValidationResult, List[str]]:
        """
        Validate workflow and attempt recovery for any issues found.
        
        Requirements: 8.11, 8.12 - Validation error handling and recovery
        
        Args:
            spec_id: The spec identifier
            
        Returns:
            Tuple of (validation_result, recovery_messages)
        """
        try:
            workflow_state = self.workflow_states.get(spec_id)
            if not workflow_state:
                return ValidationResult(
                    is_valid=False,
                    errors=[ValidationError(
                        code="WORKFLOW_NOT_FOUND",
                        message=f"Workflow not found for spec: {spec_id}"
                    )]
                ), []
            
            # Use error handler for validation and recovery
            validation_result, recovery_actions = self.error_handler.validate_and_recover(
                workflow_state=workflow_state,
                file_manager=self.file_manager
            )
            
            # Extract recovery messages
            recovery_messages = [action[1] for action in recovery_actions]
            
            return validation_result, recovery_messages
            
        except Exception as e:
            logger.error(f"Error during validation and recovery for {spec_id}: {str(e)}")
            return ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    code="VALIDATION_RECOVERY_ERROR",
                    message=f"Error during validation and recovery: {str(e)}"
                )]
            ), []