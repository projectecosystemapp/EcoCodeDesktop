"""
Tests for the error recovery service.

This module tests error classification, handling, and recovery mechanisms
for the spec-driven workflow system.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from eco_api.specs.error_recovery import (
    ErrorRecoveryService,
    ErrorCategory,
    ErrorSeverity,
    RecoveryStrategy,
    ErrorContext,
    SpecError,
    RecoveryResult
)
from eco_api.specs.models import WorkflowPhase


class TestErrorRecoveryService:
    """Test cases for ErrorRecoveryService."""
    
    @pytest.fixture
    def error_service(self):
        """Create an ErrorRecoveryService instance for testing."""
        return ErrorRecoveryService()
    
    @pytest.fixture
    def sample_context(self):
        """Create a sample error context for testing."""
        return ErrorContext(
            spec_id="test-spec",
            phase=WorkflowPhase.REQUIREMENTS,
            operation="generate_requirements",
            file_path="/test/path/requirements.md",
            user_action="create_spec"
        )
    
    def test_error_classification_file_system(self, error_service, sample_context):
        """Test classification of file system errors."""
        error = FileNotFoundError("File not found")
        
        spec_error = error_service._classify_error(error, sample_context)
        
        assert spec_error.category == ErrorCategory.FILE_SYSTEM
        assert spec_error.severity in [ErrorSeverity.MEDIUM, ErrorSeverity.LOW]
        assert "file_system" in spec_error.code
        assert spec_error.message == str(error)
    
    def test_error_classification_permission(self, error_service, sample_context):
        """Test classification of permission errors."""
        error = PermissionError("Permission denied")
        
        spec_error = error_service._classify_error(error, sample_context)
        
        assert spec_error.category == ErrorCategory.PERMISSION
        assert spec_error.severity == ErrorSeverity.HIGH
        assert "Permission denied" in spec_error.message
    
    def test_error_classification_validation(self, error_service, sample_context):
        """Test classification of validation errors."""
        error = ValueError("Invalid input format")
        
        spec_error = error_service._classify_error(error, sample_context)
        
        assert spec_error.category == ErrorCategory.VALIDATION
        assert spec_error.severity == ErrorSeverity.LOW
        assert "Invalid input format" in spec_error.message
    
    def test_error_classification_workflow_context(self, error_service):
        """Test classification based on operation context."""
        context = ErrorContext(
            spec_id="test-spec",
            operation="workflow_transition",
            phase=WorkflowPhase.DESIGN
        )
        error = RuntimeError("Invalid workflow state")
        
        spec_error = error_service._classify_error(error, context)
        
        assert spec_error.category == ErrorCategory.WORKFLOW_STATE
        assert spec_error.severity == ErrorSeverity.HIGH
    
    def test_error_classification_ai_service(self, error_service, sample_context):
        """Test classification of AI service errors."""
        error = Exception("Bedrock service unavailable")
        
        spec_error = error_service._classify_error(error, sample_context)
        
        assert spec_error.category == ErrorCategory.AI_SERVICE
        assert spec_error.severity == ErrorSeverity.MEDIUM
    
    def test_severity_determination_critical(self, error_service, sample_context):
        """Test determination of critical error severity."""
        error = MemoryError("Out of memory")
        
        spec_error = error_service._classify_error(error, sample_context)
        
        assert spec_error.severity == ErrorSeverity.CRITICAL
    
    def test_auto_recovery_detection(self, error_service):
        """Test detection of auto-recoverable errors."""
        # Network errors should be auto-recoverable
        assert error_service._can_auto_recover(ErrorCategory.NETWORK, "network_timeout")
        
        # AI service errors should be auto-recoverable
        assert error_service._can_auto_recover(ErrorCategory.AI_SERVICE, "ai_service_rate_limit")
        
        # Permission errors should not be auto-recoverable
        assert not error_service._can_auto_recover(ErrorCategory.PERMISSION, "permission_denied")
    
    def test_recovery_suggestions_generation(self, error_service, sample_context):
        """Test generation of recovery suggestions."""
        error = FileNotFoundError("File not found")
        
        suggestions = error_service._generate_recovery_suggestions(
            ErrorCategory.FILE_SYSTEM, error, sample_context
        )
        
        assert len(suggestions) > 0
        assert any("permission" in s.lower() for s in suggestions)
        assert any("disk space" in s.lower() for s in suggestions)
    
    @pytest.mark.asyncio
    async def test_handle_error_with_auto_recovery(self, error_service, sample_context):
        """Test error handling with automatic recovery."""
        # Mock an auto-recoverable error
        error = Exception("Network timeout")
        
        with patch.object(error_service, '_classify_error') as mock_classify:
            mock_error = SpecError(
                id="test-error",
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.LOW,
                code="network_timeout",
                message="Network timeout",
                context=sample_context,
                timestamp=datetime.utcnow(),
                automatic_recovery=True
            )
            mock_classify.return_value = mock_error
            
            with patch.object(error_service, '_attempt_automatic_recovery') as mock_recovery:
                mock_recovery.return_value = RecoveryResult(
                    success=True,
                    strategy_used=RecoveryStrategy.RETRY,
                    message="Recovered successfully"
                )
                
                result = await error_service.handle_error(error, sample_context)
                
                assert result.success
                assert result.strategy_used == RecoveryStrategy.RETRY
                mock_recovery.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_error_manual_intervention(self, error_service, sample_context):
        """Test error handling requiring manual intervention."""
        error = PermissionError("Permission denied")
        
        result = await error_service.handle_error(error, sample_context)
        
        assert not result.success
        assert result.strategy_used == RecoveryStrategy.MANUAL_INTERVENTION
        assert result.follow_up_required
        assert len(result.remaining_issues) > 0
    
    @pytest.mark.asyncio
    async def test_retry_with_backoff(self, error_service, sample_context):
        """Test retry mechanism with exponential backoff."""
        spec_error = SpecError(
            id="test-error",
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.LOW,
            code="network_timeout",
            message="Network timeout",
            context=sample_context,
            timestamp=datetime.utcnow()
        )
        
        # Mock asyncio.sleep to speed up test
        with patch('asyncio.sleep', new_callable=AsyncMock):
            result = await error_service._retry_with_backoff(spec_error, max_retries=2)
            
            assert result.success
            assert result.strategy_used == RecoveryStrategy.RETRY
            assert "2 retries" in result.message
    
    def test_recovery_action_creation(self, error_service, sample_context):
        """Test creation of recovery actions."""
        spec_error = SpecError(
            id="test-error",
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.MEDIUM,
            code="file_not_found",
            message="File not found",
            context=sample_context,
            timestamp=datetime.utcnow(),
            recovery_suggestions=["Check file path", "Verify permissions"]
        )
        
        # Test retry action
        retry_action = error_service._create_recovery_action(
            RecoveryStrategy.RETRY, spec_error
        )
        assert retry_action is not None
        assert retry_action.strategy == RecoveryStrategy.RETRY
        assert retry_action.automatic
        
        # Test manual intervention action
        manual_action = error_service._create_recovery_action(
            RecoveryStrategy.MANUAL_INTERVENTION, spec_error
        )
        assert manual_action is not None
        assert manual_action.strategy == RecoveryStrategy.MANUAL_INTERVENTION
        assert not manual_action.automatic
        assert len(manual_action.steps) > 0
    
    def test_error_history_tracking(self, error_service, sample_context):
        """Test error history tracking and retrieval."""
        # Create some test errors
        error1 = SpecError(
            id="error-1",
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.LOW,
            code="file_not_found",
            message="File not found",
            context=sample_context,
            timestamp=datetime.utcnow()
        )
        
        error2 = SpecError(
            id="error-2",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            code="validation_failed",
            message="Validation failed",
            context=sample_context,
            timestamp=datetime.utcnow()
        )
        
        error_service._error_history.extend([error1, error2])
        
        # Test getting all errors
        all_errors = error_service.get_error_history()
        assert len(all_errors) == 2
        
        # Test filtering by category
        file_errors = error_service.get_error_history(category=ErrorCategory.FILE_SYSTEM)
        assert len(file_errors) == 1
        assert file_errors[0].category == ErrorCategory.FILE_SYSTEM
        
        # Test filtering by spec_id
        spec_errors = error_service.get_error_history(spec_id="test-spec")
        assert len(spec_errors) == 2
    
    def test_error_statistics(self, error_service, sample_context):
        """Test error statistics generation."""
        # Add some test errors
        errors = [
            SpecError(
                id=f"error-{i}",
                category=ErrorCategory.FILE_SYSTEM if i % 2 == 0 else ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW if i % 3 == 0 else ErrorSeverity.MEDIUM,
                code=f"test_error_{i}",
                message=f"Test error {i}",
                context=sample_context,
                timestamp=datetime.utcnow()
            )
            for i in range(5)
        ]
        
        error_service._error_history.extend(errors)
        
        stats = error_service.get_error_statistics()
        
        assert stats["total_errors"] == 5
        assert "by_category" in stats
        assert "by_severity" in stats
        assert stats["by_category"][ErrorCategory.FILE_SYSTEM] == 3
        assert stats["by_category"][ErrorCategory.VALIDATION] == 2
    
    def test_empty_error_statistics(self, error_service):
        """Test error statistics with no errors."""
        stats = error_service.get_error_statistics()
        
        assert stats["total_errors"] == 0
    
    @pytest.mark.asyncio
    async def test_specific_error_handlers(self, error_service, sample_context):
        """Test specific error handler methods."""
        spec_error = SpecError(
            id="test-error",
            category=ErrorCategory.WORKFLOW_STATE,
            severity=ErrorSeverity.HIGH,
            code="workflow_invalid_transition",
            message="Invalid workflow transition",
            context=sample_context,
            timestamp=datetime.utcnow()
        )
        
        # Test workflow state error handler
        result = await error_service._handle_workflow_state_error(spec_error)
        assert not result.success
        assert result.strategy_used == RecoveryStrategy.MANUAL_INTERVENTION
        
        # Test document generation error handler
        result = await error_service._handle_document_generation_error(spec_error)
        assert result.success
        assert result.strategy_used == RecoveryStrategy.FALLBACK
        
        # Test AI service error handler
        with patch.object(error_service, '_retry_with_backoff') as mock_retry:
            mock_retry.return_value = RecoveryResult(
                success=True,
                strategy_used=RecoveryStrategy.RETRY,
                message="Retry successful"
            )
            
            result = await error_service._handle_ai_service_error(spec_error)
            assert result.success
            mock_retry.assert_called_once()
    
    def test_error_detail_extraction(self, error_service):
        """Test extraction of error details."""
        # Test error with args
        error_with_args = ValueError("Invalid value", "Additional info")
        details = error_service._extract_error_details(error_with_args)
        assert "Arguments:" in details
        
        # Test error with cause
        try:
            raise ValueError("Original error")
        except ValueError as original:
            try:
                raise RuntimeError("Wrapper error") from original
            except RuntimeError as wrapper:
                details = error_service._extract_error_details(wrapper)
                assert "Caused by:" in details
    
    def test_recovery_strategies_setup(self, error_service):
        """Test that recovery strategies are properly set up."""
        strategies = error_service._recovery_strategies
        
        # Check that all error categories have strategies
        assert ErrorCategory.WORKFLOW_STATE in strategies
        assert ErrorCategory.FILE_SYSTEM in strategies
        assert ErrorCategory.AI_SERVICE in strategies
        
        # Check that strategies are appropriate
        assert RecoveryStrategy.RETRY in strategies[ErrorCategory.AI_SERVICE]
        assert RecoveryStrategy.MANUAL_INTERVENTION in strategies[ErrorCategory.PERMISSION]
    
    def test_error_logging(self, error_service, sample_context):
        """Test error logging functionality."""
        spec_error = SpecError(
            id="test-error",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.CRITICAL,
            code="critical_validation_error",
            message="Critical validation error",
            context=sample_context,
            timestamp=datetime.utcnow()
        )
        
        with patch.object(error_service.logger, 'critical') as mock_log:
            error_service._log_error(spec_error)
            mock_log.assert_called_once()
            
            # Check that error_id is included in extra
            call_args = mock_log.call_args
            assert 'extra' in call_args.kwargs
            assert 'error_id' in call_args.kwargs['extra']