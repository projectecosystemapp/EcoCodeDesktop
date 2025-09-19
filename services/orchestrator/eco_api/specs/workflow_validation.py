"""
Comprehensive workflow validation and error handling.

This module provides validation rules, error recovery strategies, and
comprehensive validation for workflow states and transitions.

Requirements addressed:
- 8.2, 8.3: Error recovery strategies for workflow failures
- 8.7: Comprehensive workflow validation rules
- 8.11, 8.12: Validation error handling and recovery
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Tuple

from .models import (
    WorkflowPhase, WorkflowStatus, DocumentType, ValidationResult,
    ValidationError, ValidationWarning, FileOperationResult
)


logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorRecoveryStrategy(str, Enum):
    """Available error recovery strategies."""
    RETRY = "retry"
    ROLLBACK = "rollback"
    SKIP = "skip"
    MANUAL_INTERVENTION = "manual_intervention"
    RECREATE = "recreate"
    RESTORE_BACKUP = "restore_backup"


class ValidationRule(ABC):
    """Abstract base class for validation rules."""
    
    def __init__(self, name: str, description: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.name = name
        self.description = description
        self.severity = severity
    
    @abstractmethod
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        """
        Validate the given context.
        
        Args:
            context: Validation context containing workflow state and related data
            
        Returns:
            ValidationResult with validation outcome
        """
        pass


class WorkflowStateValidationRule(ValidationRule):
    """Validates basic workflow state structure and consistency."""
    
    def __init__(self):
        super().__init__(
            name="workflow_state_validation",
            description="Validates workflow state structure and consistency",
            severity=ValidationSeverity.ERROR
        )
    
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        workflow_state = context.get("workflow_state")
        if not workflow_state:
            errors.append(ValidationError(
                code="MISSING_WORKFLOW_STATE",
                message="Workflow state is missing from validation context"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Validate required attributes
        required_attrs = ["spec_id", "current_phase", "status", "approvals", "created_at", "updated_at"]
        for attr in required_attrs:
            if not hasattr(workflow_state, attr) or getattr(workflow_state, attr) is None:
                errors.append(ValidationError(
                    code="MISSING_REQUIRED_ATTRIBUTE",
                    message=f"Required workflow state attribute missing: {attr}",
                    field=attr
                ))
        
        # Validate spec_id format
        if hasattr(workflow_state, 'spec_id'):
            spec_id = workflow_state.spec_id
            if not spec_id or not isinstance(spec_id, str) or len(spec_id.strip()) == 0:
                errors.append(ValidationError(
                    code="INVALID_SPEC_ID",
                    message="Spec ID must be a non-empty string",
                    field="spec_id"
                ))
        
        # Validate timestamps
        if hasattr(workflow_state, 'created_at') and hasattr(workflow_state, 'updated_at'):
            try:
                created_at = workflow_state.created_at
                updated_at = workflow_state.updated_at
                
                if isinstance(created_at, datetime) and isinstance(updated_at, datetime):
                    if updated_at < created_at:
                        errors.append(ValidationError(
                            code="INVALID_TIMESTAMP_ORDER",
                            message="Updated timestamp cannot be before created timestamp",
                            field="updated_at"
                        ))
                    
                    # Check for reasonable timestamp values
                    now = datetime.utcnow()
                    if created_at > now + timedelta(minutes=5):  # Allow small clock skew
                        warnings.append(ValidationWarning(
                            code="FUTURE_CREATED_TIMESTAMP",
                            message="Created timestamp is in the future",
                            field="created_at",
                            suggestion="Check system clock synchronization"
                        ))
            except Exception as e:
                warnings.append(ValidationWarning(
                    code="TIMESTAMP_VALIDATION_ERROR",
                    message=f"Error validating timestamps: {str(e)}",
                    suggestion="Check timestamp format and values"
                ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class PhaseTransitionValidationRule(ValidationRule):
    """Validates workflow phase transitions."""
    
    def __init__(self):
        super().__init__(
            name="phase_transition_validation",
            description="Validates workflow phase transitions are valid",
            severity=ValidationSeverity.ERROR
        )
    
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        workflow_state = context.get("workflow_state")
        target_phase = context.get("target_phase")
        
        # Skip validation if target_phase is not provided (not a transition validation)
        if not workflow_state:
            errors.append(ValidationError(
                code="MISSING_WORKFLOW_STATE",
                message="Workflow state required for transition validation"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        if not target_phase:
            # Not a transition validation, skip this rule
            return ValidationResult(is_valid=True, errors=errors, warnings=warnings)
        
        current_phase = getattr(workflow_state, 'current_phase', None)
        if not current_phase:
            errors.append(ValidationError(
                code="MISSING_CURRENT_PHASE",
                message="Current phase is missing from workflow state"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Define valid transitions
        valid_transitions = {
            WorkflowPhase.REQUIREMENTS: [WorkflowPhase.DESIGN],
            WorkflowPhase.DESIGN: [WorkflowPhase.REQUIREMENTS, WorkflowPhase.TASKS],
            WorkflowPhase.TASKS: [WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN, WorkflowPhase.EXECUTION],
            WorkflowPhase.EXECUTION: [WorkflowPhase.EXECUTION]  # Can stay in execution
        }
        
        allowed_targets = valid_transitions.get(current_phase, [])
        if target_phase not in allowed_targets:
            errors.append(ValidationError(
                code="INVALID_PHASE_TRANSITION",
                message=f"Cannot transition from {current_phase.value} to {target_phase.value}",
                field="target_phase"
            ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class DocumentExistenceValidationRule(ValidationRule):
    """Validates that required documents exist for the current phase."""
    
    def __init__(self):
        super().__init__(
            name="document_existence_validation",
            description="Validates required documents exist for workflow phase",
            severity=ValidationSeverity.ERROR
        )
    
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        workflow_state = context.get("workflow_state")
        file_manager = context.get("file_manager")
        
        if not workflow_state:
            errors.append(ValidationError(
                code="MISSING_WORKFLOW_STATE",
                message="Workflow state required for document validation"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        if not file_manager:
            # Skip document validation if file manager is not available
            warnings.append(ValidationWarning(
                code="FILE_MANAGER_NOT_AVAILABLE",
                message="File manager not available for document validation",
                suggestion="Provide file manager for complete validation"
            ))
            return ValidationResult(is_valid=True, errors=errors, warnings=warnings)
        
        current_phase = getattr(workflow_state, 'current_phase', None)
        spec_id = getattr(workflow_state, 'spec_id', None)
        
        if not current_phase or not spec_id:
            errors.append(ValidationError(
                code="MISSING_PHASE_OR_SPEC_ID",
                message="Current phase and spec ID required for document validation"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
        
        # Define required documents for each phase
        required_documents = {
            WorkflowPhase.REQUIREMENTS: [],
            WorkflowPhase.DESIGN: [DocumentType.REQUIREMENTS],
            WorkflowPhase.TASKS: [DocumentType.REQUIREMENTS, DocumentType.DESIGN],
            WorkflowPhase.EXECUTION: [DocumentType.REQUIREMENTS, DocumentType.DESIGN, DocumentType.TASKS]
        }
        
        required_docs = required_documents.get(current_phase, [])
        
        for doc_type in required_docs:
            try:
                document, load_result = file_manager.load_document(spec_id, doc_type)
                
                if not load_result.success:
                    errors.append(ValidationError(
                        code="REQUIRED_DOCUMENT_MISSING",
                        message=f"Required document missing for phase {current_phase.value}: {doc_type.value}",
                        field=doc_type.value
                    ))
                elif document and len(document.content.strip()) == 0:
                    warnings.append(ValidationWarning(
                        code="EMPTY_REQUIRED_DOCUMENT",
                        message=f"Required document is empty: {doc_type.value}",
                        field=doc_type.value,
                        suggestion=f"Add content to {doc_type.value} document"
                    ))
                
            except Exception as e:
                errors.append(ValidationError(
                    code="DOCUMENT_VALIDATION_ERROR",
                    message=f"Error validating document {doc_type.value}: {str(e)}",
                    field=doc_type.value
                ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class ApprovalStateValidationRule(ValidationRule):
    """Validates approval states for workflow phases."""
    
    def __init__(self):
        super().__init__(
            name="approval_state_validation",
            description="Validates approval states are consistent with workflow phase",
            severity=ValidationSeverity.WARNING
        )
    
    def validate(self, context: Dict[str, Any]) -> ValidationResult:
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        workflow_state = context.get("workflow_state")
        if not workflow_state:
            return ValidationResult(is_valid=True, errors=errors, warnings=warnings)
        
        current_phase = getattr(workflow_state, 'current_phase', None)
        approvals = getattr(workflow_state, 'approvals', {})
        
        if not current_phase:
            return ValidationResult(is_valid=True, errors=errors, warnings=warnings)
        
        # Check if current phase has appropriate approval status
        phase_key = current_phase.value
        approval_status = approvals.get(phase_key)
        
        if current_phase != WorkflowPhase.REQUIREMENTS and not approval_status:
            warnings.append(ValidationWarning(
                code="MISSING_APPROVAL_STATUS",
                message=f"No approval status found for phase {current_phase.value}",
                field="approvals",
                suggestion="Set approval status for the current phase"
            ))
        
        # Check for inconsistent approval states
        from .workflow_orchestrator import ApprovalStatus
        if approval_status and hasattr(ApprovalStatus, approval_status.upper()):
            if (current_phase in [WorkflowPhase.DESIGN, WorkflowPhase.TASKS, WorkflowPhase.EXECUTION] and
                approval_status == ApprovalStatus.PENDING):
                warnings.append(ValidationWarning(
                    code="PENDING_APPROVAL_IN_ADVANCED_PHASE",
                    message=f"Phase {current_phase.value} has pending approval but workflow has progressed",
                    field="approvals",
                    suggestion="Review and approve previous phases"
                ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)


class WorkflowValidator:
    """
    Comprehensive workflow validator with configurable rules.
    
    Requirements: 8.2, 8.3, 8.7, 8.11, 8.12
    """
    
    def __init__(self):
        """Initialize the workflow validator with default rules."""
        self.validation_rules: List[ValidationRule] = [
            WorkflowStateValidationRule(),
            PhaseTransitionValidationRule(),
            DocumentExistenceValidationRule(),
            ApprovalStateValidationRule()
        ]
        self.custom_rules: Dict[str, ValidationRule] = {}
    
    def add_validation_rule(self, rule: ValidationRule) -> None:
        """
        Add a custom validation rule.
        
        Args:
            rule: The validation rule to add
        """
        self.custom_rules[rule.name] = rule
    
    def remove_validation_rule(self, rule_name: str) -> bool:
        """
        Remove a custom validation rule.
        
        Args:
            rule_name: Name of the rule to remove
            
        Returns:
            True if rule was removed, False if not found
        """
        return self.custom_rules.pop(rule_name, None) is not None
    
    def validate_workflow_state(
        self,
        workflow_state: Any,
        file_manager: Optional[Any] = None,
        target_phase: Optional[WorkflowPhase] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate a workflow state using all configured rules.
        
        Requirements: 8.7 - Comprehensive workflow validation rules
        
        Args:
            workflow_state: The workflow state to validate
            file_manager: Optional file manager for document validation
            target_phase: Optional target phase for transition validation
            additional_context: Additional context for validation
            
        Returns:
            ValidationResult with comprehensive validation results
        """
        all_errors: List[ValidationError] = []
        all_warnings: List[ValidationWarning] = []
        
        # Build validation context
        context = {
            "workflow_state": workflow_state,
            "file_manager": file_manager,
            "target_phase": target_phase,
            "timestamp": datetime.utcnow()
        }
        
        if additional_context:
            context.update(additional_context)
        
        # Run all validation rules
        all_rules = list(self.validation_rules) + list(self.custom_rules.values())
        
        for rule in all_rules:
            try:
                result = rule.validate(context)
                all_errors.extend(result.errors)
                all_warnings.extend(result.warnings)
                
            except Exception as e:
                logger.error(f"Error running validation rule {rule.name}: {str(e)}")
                all_errors.append(ValidationError(
                    code="VALIDATION_RULE_ERROR",
                    message=f"Error in validation rule {rule.name}: {str(e)}",
                    severity="error"
                ))
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def validate_workflow_transition(
        self,
        workflow_state: Any,
        target_phase: WorkflowPhase,
        file_manager: Optional[Any] = None
    ) -> ValidationResult:
        """
        Validate a specific workflow transition.
        
        Args:
            workflow_state: Current workflow state
            target_phase: Target phase for transition
            file_manager: Optional file manager for document validation
            
        Returns:
            ValidationResult for the transition
        """
        return self.validate_workflow_state(
            workflow_state=workflow_state,
            file_manager=file_manager,
            target_phase=target_phase,
            additional_context={"validation_type": "transition"}
        )


class ErrorRecoveryManager:
    """
    Manages error recovery strategies for workflow failures.
    
    Requirements: 8.2, 8.3 - Error recovery strategies for workflow failures
    """
    
    def __init__(self):
        """Initialize the error recovery manager."""
        self.recovery_strategies: Dict[str, Callable] = {
            ErrorRecoveryStrategy.RETRY: self._retry_operation,
            ErrorRecoveryStrategy.ROLLBACK: self._rollback_operation,
            ErrorRecoveryStrategy.SKIP: self._skip_operation,
            ErrorRecoveryStrategy.MANUAL_INTERVENTION: self._manual_intervention,
            ErrorRecoveryStrategy.RECREATE: self._recreate_operation,
            ErrorRecoveryStrategy.RESTORE_BACKUP: self._restore_backup
        }
    
    def determine_recovery_strategy(self, error: ValidationError, context: Dict[str, Any]) -> ErrorRecoveryStrategy:
        """
        Determine the appropriate recovery strategy for an error.
        
        Args:
            error: The validation error
            context: Error context
            
        Returns:
            Recommended recovery strategy
        """
        error_code = error.code
        severity = getattr(error, 'severity', 'error')
        
        # Strategy mapping based on error codes
        strategy_mapping = {
            "MISSING_WORKFLOW_STATE": ErrorRecoveryStrategy.RECREATE,
            "SPEC_DIRECTORY_NOT_FOUND": ErrorRecoveryStrategy.RECREATE,
            "WORKFLOW_NOT_FOUND": ErrorRecoveryStrategy.RECREATE,
            "INVALID_PHASE_TRANSITION": ErrorRecoveryStrategy.ROLLBACK,
            "REQUIRED_DOCUMENT_MISSING": ErrorRecoveryStrategy.MANUAL_INTERVENTION,
            "CHECKSUM_MISMATCH": ErrorRecoveryStrategy.RESTORE_BACKUP,
            "JSON_ERROR": ErrorRecoveryStrategy.RESTORE_BACKUP,
            "INTEGRITY_ERROR": ErrorRecoveryStrategy.RESTORE_BACKUP,
            "PERMISSION_DENIED": ErrorRecoveryStrategy.MANUAL_INTERVENTION,
            "FILESYSTEM_ERROR": ErrorRecoveryStrategy.RETRY
        }
        
        # Default strategy based on severity
        if severity == "critical":
            return ErrorRecoveryStrategy.MANUAL_INTERVENTION
        elif severity == "error":
            return strategy_mapping.get(error_code, ErrorRecoveryStrategy.MANUAL_INTERVENTION)
        else:
            return ErrorRecoveryStrategy.SKIP
    
    def execute_recovery_strategy(
        self,
        strategy: ErrorRecoveryStrategy,
        error: ValidationError,
        context: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Execute a recovery strategy.
        
        Args:
            strategy: The recovery strategy to execute
            error: The error being recovered from
            context: Recovery context
            
        Returns:
            Tuple of (success, message)
        """
        try:
            recovery_func = self.recovery_strategies.get(strategy)
            if not recovery_func:
                return False, f"Unknown recovery strategy: {strategy}"
            
            return recovery_func(error, context)
            
        except Exception as e:
            logger.error(f"Error executing recovery strategy {strategy}: {str(e)}")
            return False, f"Recovery strategy failed: {str(e)}"
    
    def _retry_operation(self, error: ValidationError, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Retry the failed operation."""
        max_retries = context.get("max_retries", 3)
        current_retry = context.get("current_retry", 0)
        
        if current_retry >= max_retries:
            return False, f"Maximum retries ({max_retries}) exceeded"
        
        # Increment retry count
        context["current_retry"] = current_retry + 1
        
        return True, f"Retrying operation (attempt {current_retry + 1}/{max_retries})"
    
    def _rollback_operation(self, error: ValidationError, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Rollback to previous state."""
        workflow_state = context.get("workflow_state")
        persistence_manager = context.get("persistence_manager")
        
        if not workflow_state or not persistence_manager:
            return False, "Cannot rollback: missing workflow state or persistence manager"
        
        try:
            # Get available versions
            versions = persistence_manager.list_workflow_versions(workflow_state.spec_id)
            if not versions:
                return False, "No previous versions available for rollback"
            
            # Restore most recent version
            latest_version = versions[0]
            restored_state, restore_result = persistence_manager.restore_workflow_version(
                workflow_state.spec_id, latest_version.version_id
            )
            
            if restore_result.success:
                return True, f"Rolled back to version {latest_version.version_id}"
            else:
                return False, f"Rollback failed: {restore_result.message}"
                
        except Exception as e:
            return False, f"Rollback error: {str(e)}"
    
    def _skip_operation(self, error: ValidationError, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Skip the failed operation."""
        return True, f"Skipped operation due to {error.code}"
    
    def _manual_intervention(self, error: ValidationError, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Require manual intervention."""
        return False, f"Manual intervention required for {error.code}: {error.message}"
    
    def _recreate_operation(self, error: ValidationError, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Recreate the failed component."""
        return False, f"Recreation required for {error.code}: {error.message}"
    
    def _restore_backup(self, error: ValidationError, context: Dict[str, Any]) -> Tuple[bool, str]:
        """Restore from backup."""
        workflow_state = context.get("workflow_state")
        persistence_manager = context.get("persistence_manager")
        
        if not workflow_state or not persistence_manager:
            return False, "Cannot restore backup: missing workflow state or persistence manager"
        
        try:
            recovered_state, recovery_result = persistence_manager.recover_workflow_state(workflow_state.spec_id)
            
            if recovery_result.success:
                return True, f"Restored from backup: {recovery_result.message}"
            else:
                return False, f"Backup restoration failed: {recovery_result.message}"
                
        except Exception as e:
            return False, f"Backup restoration error: {str(e)}"


class WorkflowErrorHandler:
    """
    Comprehensive error handler for workflow operations.
    
    Requirements: 8.2, 8.3, 8.11, 8.12
    """
    
    def __init__(self):
        """Initialize the error handler."""
        self.validator = WorkflowValidator()
        self.recovery_manager = ErrorRecoveryManager()
        self.error_history: List[Dict[str, Any]] = []
    
    def handle_workflow_error(
        self,
        error: Exception,
        workflow_state: Optional[Any] = None,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[ErrorRecoveryStrategy]]:
        """
        Handle a workflow error with appropriate recovery strategy.
        
        Requirements: 8.2, 8.3 - Error recovery strategies for workflow failures
        
        Args:
            error: The error that occurred
            workflow_state: Optional workflow state
            operation: Optional operation that failed
            context: Optional error context
            
        Returns:
            Tuple of (recovered, message, strategy_used)
        """
        try:
            # Log the error
            error_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "operation": operation,
                "spec_id": getattr(workflow_state, 'spec_id', None) if workflow_state else None
            }
            self.error_history.append(error_record)
            
            logger.error(f"Workflow error in {operation}: {str(error)}")
            
            # Convert exception to validation error
            validation_error = ValidationError(
                code=type(error).__name__.upper(),
                message=str(error),
                severity="error"
            )
            
            # Determine recovery strategy
            recovery_context = context or {}
            if workflow_state:
                recovery_context["workflow_state"] = workflow_state
            
            strategy = self.recovery_manager.determine_recovery_strategy(validation_error, recovery_context)
            
            # Execute recovery
            success, message = self.recovery_manager.execute_recovery_strategy(
                strategy, validation_error, recovery_context
            )
            
            return success, message, strategy
            
        except Exception as recovery_error:
            logger.error(f"Error during error handling: {str(recovery_error)}")
            return False, f"Error handling failed: {str(recovery_error)}", None
    
    def validate_and_recover(
        self,
        workflow_state: Any,
        file_manager: Optional[Any] = None,
        target_phase: Optional[WorkflowPhase] = None
    ) -> Tuple[ValidationResult, List[Tuple[ErrorRecoveryStrategy, str]]]:
        """
        Validate workflow state and attempt recovery for any errors.
        
        Requirements: 8.11, 8.12 - Validation error handling and recovery
        
        Args:
            workflow_state: The workflow state to validate
            file_manager: Optional file manager
            target_phase: Optional target phase
            
        Returns:
            Tuple of (validation_result, recovery_actions)
        """
        # Validate workflow state
        validation_result = self.validator.validate_workflow_state(
            workflow_state, file_manager, target_phase
        )
        
        recovery_actions: List[Tuple[ErrorRecoveryStrategy, str]] = []
        
        # Attempt recovery for each error
        for error in validation_result.errors:
            context = {
                "workflow_state": workflow_state,
                "file_manager": file_manager,
                "persistence_manager": getattr(file_manager, 'persistence_manager', None) if file_manager else None
            }
            
            strategy = self.recovery_manager.determine_recovery_strategy(error, context)
            success, message = self.recovery_manager.execute_recovery_strategy(strategy, error, context)
            
            recovery_actions.append((strategy, message))
            
            if success:
                logger.info(f"Successfully recovered from error {error.code}: {message}")
            else:
                logger.warning(f"Recovery failed for error {error.code}: {message}")
        
        return validation_result, recovery_actions
    
    def get_error_history(self, spec_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get error history for debugging and analysis.
        
        Args:
            spec_id: Optional spec ID to filter by
            limit: Maximum number of errors to return
            
        Returns:
            List of error records
        """
        filtered_errors = self.error_history
        
        if spec_id:
            filtered_errors = [
                error for error in filtered_errors
                if error.get("spec_id") == spec_id
            ]
        
        # Return most recent errors first
        return list(reversed(filtered_errors))[-limit:]
    
    def clear_error_history(self, spec_id: Optional[str] = None) -> None:
        """
        Clear error history.
        
        Args:
            spec_id: Optional spec ID to clear errors for (clears all if None)
        """
        if spec_id:
            self.error_history = [
                error for error in self.error_history
                if error.get("spec_id") != spec_id
            ]
        else:
            self.error_history.clear()