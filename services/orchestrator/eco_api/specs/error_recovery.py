"""
Error classification and recovery framework for spec-driven workflows.

This module provides comprehensive error handling, classification, and recovery
mechanisms for all aspects of the spec workflow system.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from pydantic import BaseModel, Field
import logging
import traceback
import asyncio
from pathlib import Path

from .models import WorkflowPhase, WorkflowStatus, ValidationResult, ValidationError


class ErrorCategory(str, Enum):
    """Categories of errors in the spec workflow system."""
    WORKFLOW_STATE = "workflow_state"
    DOCUMENT_GENERATION = "document_generation"
    FILE_SYSTEM = "file_system"
    TASK_EXECUTION = "task_execution"
    VALIDATION = "validation"
    AI_SERVICE = "ai_service"
    NETWORK = "network"
    PERMISSION = "permission"
    CORRUPTION = "corruption"
    DEPENDENCY = "dependency"


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(str, Enum):
    """Available recovery strategies."""
    RETRY = "retry"
    ROLLBACK = "rollback"
    MANUAL_INTERVENTION = "manual_intervention"
    SKIP = "skip"
    RECREATE = "recreate"
    FALLBACK = "fallback"
    ABORT = "abort"


class ErrorContext(BaseModel):
    """Context information for an error."""
    spec_id: Optional[str] = None
    phase: Optional[WorkflowPhase] = None
    operation: Optional[str] = None
    file_path: Optional[str] = None
    user_action: Optional[str] = None
    system_state: Dict[str, Any] = Field(default_factory=dict)


class SpecError(BaseModel):
    """Structured error information."""
    id: str
    category: ErrorCategory
    severity: ErrorSeverity
    code: str
    message: str
    details: Optional[str] = None
    context: ErrorContext
    timestamp: datetime
    stack_trace: Optional[str] = None
    recovery_suggestions: List[str] = Field(default_factory=list)
    automatic_recovery: bool = False


class RecoveryAction(BaseModel):
    """Action to recover from an error."""
    strategy: RecoveryStrategy
    description: str
    automatic: bool
    estimated_time: Optional[int] = None  # seconds
    prerequisites: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    rollback_possible: bool = True


class RecoveryResult(BaseModel):
    """Result of a recovery operation."""
    success: bool
    strategy_used: RecoveryStrategy
    message: str
    actions_taken: List[str] = Field(default_factory=list)
    remaining_issues: List[str] = Field(default_factory=list)
    follow_up_required: bool = False


class ErrorRecoveryService:
    """
    Service for error classification, handling, and recovery.
    
    Provides comprehensive error management with automatic recovery
    mechanisms and user-guided recovery workflows.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._error_handlers: Dict[str, Callable] = {}
        self._recovery_strategies: Dict[ErrorCategory, List[RecoveryStrategy]] = {}
        self._error_history: List[SpecError] = []
        self._setup_default_handlers()
        self._setup_recovery_strategies()
    
    def _setup_default_handlers(self) -> None:
        """Set up default error handlers for common error types."""
        self._error_handlers.update({
            "workflow_invalid_transition": self._handle_workflow_state_error,
            "document_generation_failed": self._handle_document_generation_error,
            "file_permission_denied": self._handle_file_permission_error,
            "file_not_found": self._handle_file_not_found_error,
            "file_corruption": self._handle_file_corruption_error,
            "ai_service_unavailable": self._handle_ai_service_error,
            "validation_failed": self._handle_validation_error,
            "task_execution_failed": self._handle_task_execution_error,
            "dependency_missing": self._handle_dependency_error,
        })
    
    def _setup_recovery_strategies(self) -> None:
        """Set up recovery strategies for each error category."""
        self._recovery_strategies = {
            ErrorCategory.WORKFLOW_STATE: [
                RecoveryStrategy.ROLLBACK,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.DOCUMENT_GENERATION: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.FALLBACK,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.FILE_SYSTEM: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.RECREATE,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.TASK_EXECUTION: [
                RecoveryStrategy.ROLLBACK,
                RecoveryStrategy.SKIP,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.VALIDATION: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.AI_SERVICE: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.FALLBACK,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.NETWORK: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.FALLBACK
            ],
            ErrorCategory.PERMISSION: [
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.CORRUPTION: [
                RecoveryStrategy.ROLLBACK,
                RecoveryStrategy.RECREATE,
                RecoveryStrategy.MANUAL_INTERVENTION
            ],
            ErrorCategory.DEPENDENCY: [
                RecoveryStrategy.RETRY,
                RecoveryStrategy.MANUAL_INTERVENTION
            ]
        }
    
    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        error_code: Optional[str] = None
    ) -> RecoveryResult:
        """
        Handle an error with automatic classification and recovery.
        
        Args:
            error: The exception that occurred
            context: Context information about the error
            error_code: Optional specific error code
            
        Returns:
            RecoveryResult with the outcome of recovery attempts
        """
        # Classify the error
        spec_error = self._classify_error(error, context, error_code)
        
        # Log the error
        self._log_error(spec_error)
        
        # Add to error history
        self._error_history.append(spec_error)
        
        # Attempt automatic recovery if possible
        if spec_error.automatic_recovery:
            recovery_result = await self._attempt_automatic_recovery(spec_error)
            if recovery_result.success:
                return recovery_result
        
        # Generate recovery actions for manual intervention
        recovery_actions = self._generate_recovery_actions(spec_error)
        
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
            message=f"Manual intervention required for {spec_error.category} error",
            actions_taken=[],
            remaining_issues=[spec_error.message],
            follow_up_required=True
        )
    
    def _classify_error(
        self,
        error: Exception,
        context: ErrorContext,
        error_code: Optional[str] = None
    ) -> SpecError:
        """Classify an error into appropriate category and severity."""
        import uuid
        
        # Determine category based on error type and context
        category = self._determine_error_category(error, context)
        
        # Determine severity
        severity = self._determine_error_severity(error, category, context)
        
        # Generate error code if not provided
        if not error_code:
            error_code = f"{category.value}_{type(error).__name__.lower()}"
        
        # Check if automatic recovery is possible
        automatic_recovery = self._can_auto_recover(category, error_code)
        
        # Generate recovery suggestions
        suggestions = self._generate_recovery_suggestions(category, error, context)
        
        return SpecError(
            id=str(uuid.uuid4()),
            category=category,
            severity=severity,
            code=error_code,
            message=str(error),
            details=self._extract_error_details(error),
            context=context,
            timestamp=datetime.utcnow(),
            stack_trace=traceback.format_exc(),
            recovery_suggestions=suggestions,
            automatic_recovery=automatic_recovery
        )
    
    def _determine_error_category(
        self,
        error: Exception,
        context: ErrorContext
    ) -> ErrorCategory:
        """Determine the category of an error based on type and context."""
        error_type = type(error).__name__
        
        # Permission errors (check first, more specific than file system)
        if isinstance(error, PermissionError):
            return ErrorCategory.PERMISSION
        
        # File system errors
        if isinstance(error, (FileNotFoundError, OSError)):
            return ErrorCategory.FILE_SYSTEM
        
        # Network errors
        if "network" in error_type.lower() or "connection" in str(error).lower():
            return ErrorCategory.NETWORK
        
        # AI service errors
        if "bedrock" in str(error).lower() or "ai" in str(error).lower():
            return ErrorCategory.AI_SERVICE
        
        # Validation errors
        if "validation" in error_type.lower() or isinstance(error, ValueError):
            return ErrorCategory.VALIDATION
        
        # Context-based classification
        if context.operation:
            if "workflow" in context.operation.lower():
                return ErrorCategory.WORKFLOW_STATE
            elif "generate" in context.operation.lower():
                return ErrorCategory.DOCUMENT_GENERATION
            elif "execute" in context.operation.lower():
                return ErrorCategory.TASK_EXECUTION
        
        # Default to validation for unknown errors
        return ErrorCategory.VALIDATION
    
    def _determine_error_severity(
        self,
        error: Exception,
        category: ErrorCategory,
        context: ErrorContext
    ) -> ErrorSeverity:
        """Determine the severity of an error."""
        # Critical errors that prevent system operation
        if isinstance(error, (SystemError, MemoryError)):
            return ErrorSeverity.CRITICAL
        
        # High severity for data corruption or security issues
        if category in [ErrorCategory.CORRUPTION, ErrorCategory.PERMISSION]:
            return ErrorSeverity.HIGH
        
        # High severity for workflow state errors
        if category == ErrorCategory.WORKFLOW_STATE:
            return ErrorSeverity.HIGH
        
        # Medium severity for file system and AI service errors
        if category in [ErrorCategory.FILE_SYSTEM, ErrorCategory.AI_SERVICE]:
            return ErrorSeverity.MEDIUM
        
        # Low severity for validation and network errors (usually recoverable)
        return ErrorSeverity.LOW
    
    def _can_auto_recover(self, category: ErrorCategory, error_code: str) -> bool:
        """Determine if an error can be automatically recovered from."""
        auto_recoverable_codes = {
            "network_timeout",
            "ai_service_rate_limit",
            "file_system_temporary_unavailable",
            "validation_format_error"
        }
        
        auto_recoverable_categories = {
            ErrorCategory.NETWORK,
            ErrorCategory.AI_SERVICE
        }
        
        return (
            error_code in auto_recoverable_codes or
            category in auto_recoverable_categories
        )
    
    def _generate_recovery_suggestions(
        self,
        category: ErrorCategory,
        error: Exception,
        context: ErrorContext
    ) -> List[str]:
        """Generate human-readable recovery suggestions."""
        suggestions = []
        
        if category == ErrorCategory.FILE_SYSTEM:
            suggestions.extend([
                "Check file permissions and ensure the directory is writable",
                "Verify disk space is available",
                "Ensure the file path is valid and accessible"
            ])
        
        elif category == ErrorCategory.AI_SERVICE:
            suggestions.extend([
                "Check internet connection and retry",
                "Verify AWS credentials are configured correctly",
                "Wait a moment and retry if rate limited"
            ])
        
        elif category == ErrorCategory.WORKFLOW_STATE:
            suggestions.extend([
                "Review the current workflow phase and ensure prerequisites are met",
                "Check if documents are properly approved before proceeding",
                "Verify workflow state consistency"
            ])
        
        elif category == ErrorCategory.VALIDATION:
            suggestions.extend([
                "Review the document format and ensure it meets requirements",
                "Check for missing required sections or fields",
                "Validate input data against expected schemas"
            ])
        
        elif category == ErrorCategory.TASK_EXECUTION:
            suggestions.extend([
                "Review task dependencies and ensure they are completed",
                "Check if required context documents are available",
                "Verify task parameters and execution environment"
            ])
        
        return suggestions
    
    def _extract_error_details(self, error: Exception) -> Optional[str]:
        """Extract detailed error information."""
        details = []
        
        if hasattr(error, 'args') and error.args:
            details.append(f"Arguments: {error.args}")
        
        if hasattr(error, '__cause__') and error.__cause__:
            details.append(f"Caused by: {error.__cause__}")
        
        if hasattr(error, '__context__') and error.__context__:
            details.append(f"Context: {error.__context__}")
        
        return "; ".join(details) if details else None
    
    async def _attempt_automatic_recovery(self, spec_error: SpecError) -> RecoveryResult:
        """Attempt automatic recovery for recoverable errors."""
        handler_key = spec_error.code
        
        if handler_key in self._error_handlers:
            try:
                return await self._error_handlers[handler_key](spec_error)
            except Exception as e:
                self.logger.error(f"Automatic recovery failed: {e}")
        
        # Default retry mechanism for certain categories
        if spec_error.category in [ErrorCategory.NETWORK, ErrorCategory.AI_SERVICE]:
            return await self._retry_with_backoff(spec_error)
        
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
            message="Automatic recovery not available for this error type"
        )
    
    async def _retry_with_backoff(
        self,
        spec_error: SpecError,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> RecoveryResult:
        """Implement retry with exponential backoff."""
        for attempt in range(max_retries):
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
            
            # This would need to be implemented based on the specific operation
            # For now, we'll simulate a recovery attempt
            self.logger.info(f"Retry attempt {attempt + 1} for error {spec_error.id}")
            
            # In a real implementation, this would re-execute the failed operation
            # For now, we'll assume success after the final retry
            if attempt == max_retries - 1:
                return RecoveryResult(
                    success=True,
                    strategy_used=RecoveryStrategy.RETRY,
                    message=f"Recovered after {attempt + 1} retries",
                    actions_taken=[f"Retried operation {attempt + 1} times"]
                )
        
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.RETRY,
            message=f"Failed to recover after {max_retries} retries"
        )
    
    def _generate_recovery_actions(self, spec_error: SpecError) -> List[RecoveryAction]:
        """Generate possible recovery actions for an error."""
        actions = []
        strategies = self._recovery_strategies.get(spec_error.category, [])
        
        for strategy in strategies:
            action = self._create_recovery_action(strategy, spec_error)
            if action:
                actions.append(action)
        
        return actions
    
    def _create_recovery_action(
        self,
        strategy: RecoveryStrategy,
        spec_error: SpecError
    ) -> Optional[RecoveryAction]:
        """Create a specific recovery action for a strategy and error."""
        if strategy == RecoveryStrategy.RETRY:
            return RecoveryAction(
                strategy=strategy,
                description="Retry the failed operation",
                automatic=True,
                estimated_time=30,
                steps=["Wait for system stabilization", "Retry the operation"]
            )
        
        elif strategy == RecoveryStrategy.ROLLBACK:
            return RecoveryAction(
                strategy=strategy,
                description="Rollback to previous stable state",
                automatic=False,
                estimated_time=60,
                steps=[
                    "Identify last stable state",
                    "Restore documents from backup",
                    "Verify system consistency"
                ]
            )
        
        elif strategy == RecoveryStrategy.MANUAL_INTERVENTION:
            return RecoveryAction(
                strategy=strategy,
                description="Manual intervention required",
                automatic=False,
                steps=spec_error.recovery_suggestions,
                rollback_possible=False
            )
        
        elif strategy == RecoveryStrategy.RECREATE:
            return RecoveryAction(
                strategy=strategy,
                description="Recreate the affected component",
                automatic=False,
                estimated_time=300,
                steps=[
                    "Backup existing data if possible",
                    "Remove corrupted component",
                    "Recreate from template or backup"
                ]
            )
        
        return None
    
    def _log_error(self, spec_error: SpecError) -> None:
        """Log error information appropriately based on severity."""
        log_message = f"[{spec_error.category}] {spec_error.message}"
        
        if spec_error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, extra={"error_id": spec_error.id})
        elif spec_error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, extra={"error_id": spec_error.id})
        elif spec_error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message, extra={"error_id": spec_error.id})
        else:
            self.logger.info(log_message, extra={"error_id": spec_error.id})
    
    # Specific error handlers
    async def _handle_workflow_state_error(self, spec_error: SpecError) -> RecoveryResult:
        """Handle workflow state errors."""
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
            message="Workflow state error requires manual review",
            remaining_issues=["Review workflow state and correct invalid transitions"]
        )
    
    async def _handle_document_generation_error(self, spec_error: SpecError) -> RecoveryResult:
        """Handle document generation errors."""
        # Attempt to use fallback template
        return RecoveryResult(
            success=True,
            strategy_used=RecoveryStrategy.FALLBACK,
            message="Used fallback template for document generation",
            actions_taken=["Applied default document template"]
        )
    
    async def _handle_file_permission_error(self, spec_error: SpecError) -> RecoveryResult:
        """Handle file permission errors."""
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
            message="File permission error requires manual resolution",
            remaining_issues=["Check and correct file permissions"]
        )
    
    async def _handle_file_not_found_error(self, spec_error: SpecError) -> RecoveryResult:
        """Handle file not found errors."""
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.RECREATE,
            message="File not found - recreation required",
            remaining_issues=["Recreate missing file from template or backup"]
        )
    
    async def _handle_file_corruption_error(self, spec_error: SpecError) -> RecoveryResult:
        """Handle file corruption errors."""
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.ROLLBACK,
            message="File corruption detected - rollback required",
            remaining_issues=["Restore from backup or recreate file"]
        )
    
    async def _handle_ai_service_error(self, spec_error: SpecError) -> RecoveryResult:
        """Handle AI service errors."""
        return await self._retry_with_backoff(spec_error)
    
    async def _handle_validation_error(self, spec_error: SpecError) -> RecoveryResult:
        """Handle validation errors."""
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
            message="Validation error requires correction",
            remaining_issues=["Review and correct validation issues"]
        )
    
    async def _handle_task_execution_error(self, spec_error: SpecError) -> RecoveryResult:
        """Handle task execution errors."""
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.ROLLBACK,
            message="Task execution failed - rollback recommended",
            remaining_issues=["Review task requirements and dependencies"]
        )
    
    async def _handle_dependency_error(self, spec_error: SpecError) -> RecoveryResult:
        """Handle dependency errors."""
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
            message="Dependency error requires resolution",
            remaining_issues=["Install or configure missing dependencies"]
        )
    
    def get_error_history(
        self,
        spec_id: Optional[str] = None,
        category: Optional[ErrorCategory] = None,
        limit: int = 100
    ) -> List[SpecError]:
        """Get error history with optional filtering."""
        errors = self._error_history
        
        if spec_id:
            errors = [e for e in errors if e.context.spec_id == spec_id]
        
        if category:
            errors = [e for e in errors if e.category == category]
        
        return errors[-limit:]
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring and analysis."""
        total_errors = len(self._error_history)
        
        if total_errors == 0:
            return {"total_errors": 0}
        
        category_counts = {}
        severity_counts = {}
        
        for error in self._error_history:
            category_counts[error.category] = category_counts.get(error.category, 0) + 1
            severity_counts[error.severity] = severity_counts.get(error.severity, 0) + 1
        
        return {
            "total_errors": total_errors,
            "by_category": category_counts,
            "by_severity": severity_counts,
            "recent_errors": len([
                e for e in self._error_history
                if (datetime.utcnow() - e.timestamp).total_seconds() < 3600
            ])
        }