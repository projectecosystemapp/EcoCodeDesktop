"""
Integration tests for workflow orchestrator and state transitions.

Tests the complete workflow orchestration system including state management,
transitions, persistence, and error handling.

Requirements tested:
- 1.8, 1.9, 1.10, 1.11: Workflow state transitions and approval handling
- 8.1, 8.7: Workflow state management and validation
- 8.2, 8.3: Error recovery strategies
- 8.6, 8.10, 8.11: Persistence and recovery mechanisms
"""

import json
import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from eco_api.specs.workflow_orchestrator import (
    WorkflowOrchestrator, WorkflowState, ApprovalStatus, WorkflowTransition
)
from eco_api.specs.workflow_validation import (
    WorkflowValidator, ErrorRecoveryManager, WorkflowErrorHandler
)
from eco_api.specs.models import (
    WorkflowPhase, WorkflowStatus, DocumentType, ValidationError
)


class TestWorkflowOrchestrator:
    """Test suite for WorkflowOrchestrator class."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def orchestrator(self, temp_workspace):
        """Create a WorkflowOrchestrator instance for testing."""
        return WorkflowOrchestrator(temp_workspace)
    
    def test_create_spec_workflow_success(self, orchestrator):
        """Test successful spec workflow creation."""
        feature_idea = "User authentication system with OAuth support"
        
        workflow_state, result = orchestrator.create_spec_workflow(feature_idea)
        
        assert result.success
        assert workflow_state is not None
        assert workflow_state.spec_id == "user-authentication-system-with-oauth-support"
        assert workflow_state.current_phase == WorkflowPhase.REQUIREMENTS
        assert workflow_state.status == WorkflowStatus.DRAFT
        assert "requirements" in workflow_state.approvals
        assert workflow_state.approvals["requirements"] == ApprovalStatus.PENDING
    
    def test_create_spec_workflow_with_custom_name(self, orchestrator):
        """Test spec workflow creation with custom feature name."""
        feature_idea = "Complex feature idea"
        feature_name = "custom-feature-name"
        
        workflow_state, result = orchestrator.create_spec_workflow(feature_idea, feature_name)
        
        assert result.success
        assert workflow_state.spec_id == feature_name
    
    def test_create_spec_workflow_duplicate_name(self, orchestrator):
        """Test handling of duplicate feature names."""
        feature_idea = "Test feature"
        
        # Create first workflow
        workflow_state1, result1 = orchestrator.create_spec_workflow(feature_idea)
        assert result1.success
        
        # Try to create second workflow with same idea (should generate same name)
        workflow_state2, result2 = orchestrator.create_spec_workflow(feature_idea)
        assert not result2.success
        assert "not unique" in result2.message.lower()
    
    def test_get_workflow_state(self, orchestrator):
        """Test retrieving workflow state."""
        feature_idea = "Test feature for state retrieval"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Retrieve workflow state
        retrieved_state = orchestrator.get_workflow_state(spec_id)
        
        assert retrieved_state is not None
        assert retrieved_state.spec_id == spec_id
        assert retrieved_state.current_phase == WorkflowPhase.REQUIREMENTS
    
    def test_get_workflow_state_not_found(self, orchestrator):
        """Test retrieving non-existent workflow state."""
        retrieved_state = orchestrator.get_workflow_state("non-existent-spec")
        assert retrieved_state is None
    
    def test_transition_workflow_forward_success(self, orchestrator):
        """Test successful forward workflow transition."""
        feature_idea = "Test feature for transition"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Mock file manager to return valid documents
        with patch.object(orchestrator.file_manager, 'load_document') as mock_load:
            mock_doc = Mock()
            mock_doc.content = "# Requirements\n\nSome requirements content"
            mock_result = Mock()
            mock_result.success = True
            mock_load.return_value = (mock_doc, mock_result)
            
            # Transition to design phase with approval
            updated_state, validation = orchestrator.transition_workflow(
                spec_id, WorkflowPhase.DESIGN, approval=True
            )
            
            assert validation.is_valid
            assert updated_state is not None
            assert updated_state.current_phase == WorkflowPhase.DESIGN
            assert updated_state.approvals["requirements"] == ApprovalStatus.APPROVED
    
    def test_transition_workflow_without_approval(self, orchestrator):
        """Test workflow transition without required approval."""
        feature_idea = "Test feature for transition without approval"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Try to transition without approval
        updated_state, validation = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.DESIGN, approval=False
        )
        
        assert validation.is_valid  # Should be valid but not transition
        assert updated_state.current_phase == WorkflowPhase.REQUIREMENTS  # Should stay in requirements
        assert updated_state.approvals["requirements"] == ApprovalStatus.NEEDS_REVISION
    
    def test_transition_workflow_invalid_transition(self, orchestrator):
        """Test invalid workflow transition."""
        feature_idea = "Test feature for invalid transition"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Try invalid transition (requirements to execution)
        updated_state, validation = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.EXECUTION, approval=True
        )
        
        assert not validation.is_valid
        assert updated_state is None
        assert any("transition" in error.code.lower() or "invalid" in error.message.lower() for error in validation.errors)
    
    def test_transition_workflow_backward(self, orchestrator):
        """Test backward workflow transition."""
        feature_idea = "Test feature for backward transition"
        
        # Create workflow and move to design phase
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Manually set to design phase for testing
        workflow_state.current_phase = WorkflowPhase.DESIGN
        orchestrator.workflow_states[spec_id] = workflow_state
        
        # Transition back to requirements (should fail due to missing documents)
        updated_state, validation = orchestrator.transition_workflow(
            spec_id, WorkflowPhase.REQUIREMENTS
        )
        
        # This should fail because we're in design phase without required documents
        # But the transition itself is valid, so we should get an error about missing documents
        assert not validation.is_valid
        assert any("REQUIRED_DOCUMENT_MISSING" in error.code for error in validation.errors)
        assert updated_state is None  # Transition should not succeed
    
    def test_approve_phase_success(self, orchestrator):
        """Test successful phase approval."""
        feature_idea = "Test feature for approval"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Approve requirements phase
        updated_state, validation = orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, True, "Looks good!"
        )
        
        assert validation.is_valid
        assert updated_state.approvals["requirements"] == ApprovalStatus.APPROVED
        assert "requirements_feedback" in updated_state.metadata
    
    def test_approve_phase_rejection(self, orchestrator):
        """Test phase rejection."""
        feature_idea = "Test feature for rejection"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Reject requirements phase
        updated_state, validation = orchestrator.approve_phase(
            spec_id, WorkflowPhase.REQUIREMENTS, False, "Needs more detail"
        )
        
        assert validation.is_valid
        assert updated_state.approvals["requirements"] == ApprovalStatus.NEEDS_REVISION
        assert updated_state.metadata["requirements_feedback"] == "Needs more detail"
    
    def test_approve_phase_wrong_phase(self, orchestrator):
        """Test approving wrong phase."""
        feature_idea = "Test feature for wrong phase approval"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Try to approve design phase while in requirements
        updated_state, validation = orchestrator.approve_phase(
            spec_id, WorkflowPhase.DESIGN, True
        )
        
        assert not validation.is_valid
        assert updated_state is None
        assert any("Cannot approve" in error.message for error in validation.errors)
    
    def test_list_workflows(self, orchestrator):
        """Test listing workflows."""
        # Create multiple workflows
        workflows = [
            "First test feature",
            "Second test feature",
            "Third test feature"
        ]
        
        created_specs = []
        for feature_idea in workflows:
            workflow_state, result = orchestrator.create_spec_workflow(feature_idea)
            if result.success:
                created_specs.append(workflow_state.spec_id)
        
        # List workflows
        workflow_list = orchestrator.list_workflows()
        
        assert len(workflow_list) >= len(created_specs)
        spec_ids = [spec.id for spec in workflow_list]
        
        for spec_id in created_specs:
            assert spec_id in spec_ids
    
    def test_validate_workflow(self, orchestrator):
        """Test workflow validation."""
        feature_idea = "Test feature for validation"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Validate workflow
        validation = orchestrator.validate_workflow(spec_id)
        
        # Should have warnings about missing documents but no errors
        assert validation.is_valid or len(validation.errors) == 0
        # May have warnings about missing documents
    
    def test_validate_workflow_not_found(self, orchestrator):
        """Test validation of non-existent workflow."""
        validation = orchestrator.validate_workflow("non-existent-spec")
        
        assert not validation.is_valid
        assert any("not found" in error.message.lower() for error in validation.errors)
    
    def test_workflow_persistence_and_recovery(self, orchestrator):
        """Test workflow persistence and recovery."""
        feature_idea = "Test feature for persistence"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Create new orchestrator instance (simulates restart)
        new_orchestrator = WorkflowOrchestrator(orchestrator.workspace_root)
        
        # Check if workflow was loaded
        recovered_state = new_orchestrator.get_workflow_state(spec_id)
        
        assert recovered_state is not None
        assert recovered_state.spec_id == spec_id
        assert recovered_state.current_phase == WorkflowPhase.REQUIREMENTS
    
    def test_workflow_versions(self, orchestrator):
        """Test workflow versioning."""
        feature_idea = "Test feature for versioning"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Make some changes to create versions
        orchestrator.approve_phase(spec_id, WorkflowPhase.REQUIREMENTS, True)
        
        # Get versions
        versions = orchestrator.get_workflow_versions(spec_id)
        
        assert len(versions) >= 1  # Should have at least initial version
    
    def test_restore_workflow_version(self, orchestrator):
        """Test restoring workflow version."""
        feature_idea = "Test feature for version restore"
        
        # Create workflow
        workflow_state, _ = orchestrator.create_spec_workflow(feature_idea)
        spec_id = workflow_state.spec_id
        
        # Make changes
        orchestrator.approve_phase(spec_id, WorkflowPhase.REQUIREMENTS, True)
        
        # Get versions
        versions = orchestrator.get_workflow_versions(spec_id)
        if versions:
            version_id = versions[0].version_id
            
            # Restore version
            restored_state, validation = orchestrator.restore_workflow_version(spec_id, version_id)
            
            assert validation.is_valid
            assert restored_state is not None


class TestWorkflowValidator:
    """Test suite for WorkflowValidator class."""
    
    @pytest.fixture
    def validator(self):
        """Create a WorkflowValidator instance for testing."""
        return WorkflowValidator()
    
    @pytest.fixture
    def mock_workflow_state(self):
        """Create a mock workflow state for testing."""
        return WorkflowState(
            spec_id="test-spec",
            current_phase=WorkflowPhase.REQUIREMENTS,
            status=WorkflowStatus.DRAFT,
            approvals={"requirements": ApprovalStatus.PENDING},
            metadata={"test": "data"}
        )
    
    def test_validate_workflow_state_success(self, validator, mock_workflow_state):
        """Test successful workflow state validation."""
        result = validator.validate_workflow_state(mock_workflow_state)
        
        # Should pass basic validation
        assert result.is_valid or len(result.errors) == 0
    
    def test_validate_workflow_state_missing_state(self, validator):
        """Test validation with missing workflow state."""
        result = validator.validate_workflow_state(None)
        
        assert not result.is_valid
        assert any("missing" in error.message.lower() for error in result.errors)
    
    def test_validate_workflow_transition_valid(self, validator, mock_workflow_state):
        """Test valid workflow transition validation."""
        result = validator.validate_workflow_transition(
            mock_workflow_state, WorkflowPhase.DESIGN
        )
        
        # Requirements to Design should be valid
        assert result.is_valid or len([e for e in result.errors if "transition" in e.code.lower()]) == 0
    
    def test_validate_workflow_transition_invalid(self, validator, mock_workflow_state):
        """Test invalid workflow transition validation."""
        result = validator.validate_workflow_transition(
            mock_workflow_state, WorkflowPhase.EXECUTION
        )
        
        # Requirements to Execution should be invalid
        assert not result.is_valid
        assert any("transition" in error.code.lower() for error in result.errors)
    
    def test_add_custom_validation_rule(self, validator):
        """Test adding custom validation rule."""
        from eco_api.specs.workflow_validation import ValidationRule, ValidationSeverity
        
        class CustomRule(ValidationRule):
            def __init__(self):
                super().__init__("custom_rule", "Custom test rule", ValidationSeverity.WARNING)
            
            def validate(self, context):
                from eco_api.specs.models import ValidationResult, ValidationWarning
                return ValidationResult(
                    is_valid=True,
                    warnings=[ValidationWarning(
                        code="CUSTOM_WARNING",
                        message="Custom validation warning"
                    )]
                )
        
        custom_rule = CustomRule()
        validator.add_validation_rule(custom_rule)
        
        # Validate with custom rule
        mock_state = WorkflowState(
            spec_id="test",
            current_phase=WorkflowPhase.REQUIREMENTS,
            status=WorkflowStatus.DRAFT
        )
        
        result = validator.validate_workflow_state(mock_state)
        
        # Should include custom warning
        assert any("CUSTOM_WARNING" in warning.code for warning in result.warnings)
    
    def test_remove_validation_rule(self, validator):
        """Test removing validation rule."""
        from eco_api.specs.workflow_validation import ValidationRule, ValidationSeverity
        
        class RemovableRule(ValidationRule):
            def __init__(self):
                super().__init__("removable_rule", "Removable test rule")
            
            def validate(self, context):
                from eco_api.specs.models import ValidationResult
                return ValidationResult(is_valid=True)
        
        rule = RemovableRule()
        validator.add_validation_rule(rule)
        
        # Remove rule
        removed = validator.remove_validation_rule("removable_rule")
        assert removed
        
        # Try to remove again
        removed_again = validator.remove_validation_rule("removable_rule")
        assert not removed_again


class TestErrorRecoveryManager:
    """Test suite for ErrorRecoveryManager class."""
    
    @pytest.fixture
    def recovery_manager(self):
        """Create an ErrorRecoveryManager instance for testing."""
        return ErrorRecoveryManager()
    
    def test_determine_recovery_strategy(self, recovery_manager):
        """Test recovery strategy determination."""
        from eco_api.specs.workflow_validation import ErrorRecoveryStrategy
        
        # Test different error codes
        test_cases = [
            (ValidationError(code="MISSING_WORKFLOW_STATE", message="Test"), ErrorRecoveryStrategy.RECREATE),
            (ValidationError(code="INVALID_PHASE_TRANSITION", message="Test"), ErrorRecoveryStrategy.ROLLBACK),
            (ValidationError(code="CHECKSUM_MISMATCH", message="Test"), ErrorRecoveryStrategy.RESTORE_BACKUP),
            (ValidationError(code="PERMISSION_DENIED", message="Test"), ErrorRecoveryStrategy.MANUAL_INTERVENTION),
        ]
        
        for error, expected_strategy in test_cases:
            strategy = recovery_manager.determine_recovery_strategy(error, {})
            assert strategy == expected_strategy
    
    def test_execute_recovery_strategy_retry(self, recovery_manager):
        """Test retry recovery strategy."""
        from eco_api.specs.workflow_validation import ErrorRecoveryStrategy
        
        error = ValidationError(code="TEST_ERROR", message="Test error")
        context = {"max_retries": 3, "current_retry": 0}
        
        success, message = recovery_manager.execute_recovery_strategy(
            ErrorRecoveryStrategy.RETRY, error, context
        )
        
        assert success
        assert "Retrying" in message
        assert context["current_retry"] == 1
    
    def test_execute_recovery_strategy_retry_exhausted(self, recovery_manager):
        """Test retry recovery strategy when retries exhausted."""
        from eco_api.specs.workflow_validation import ErrorRecoveryStrategy
        
        error = ValidationError(code="TEST_ERROR", message="Test error")
        context = {"max_retries": 3, "current_retry": 3}
        
        success, message = recovery_manager.execute_recovery_strategy(
            ErrorRecoveryStrategy.RETRY, error, context
        )
        
        assert not success
        assert "Maximum retries" in message
    
    def test_execute_recovery_strategy_skip(self, recovery_manager):
        """Test skip recovery strategy."""
        from eco_api.specs.workflow_validation import ErrorRecoveryStrategy
        
        error = ValidationError(code="TEST_ERROR", message="Test error")
        context = {}
        
        success, message = recovery_manager.execute_recovery_strategy(
            ErrorRecoveryStrategy.SKIP, error, context
        )
        
        assert success
        assert "Skipped" in message
    
    def test_execute_recovery_strategy_manual_intervention(self, recovery_manager):
        """Test manual intervention recovery strategy."""
        from eco_api.specs.workflow_validation import ErrorRecoveryStrategy
        
        error = ValidationError(code="TEST_ERROR", message="Test error")
        context = {}
        
        success, message = recovery_manager.execute_recovery_strategy(
            ErrorRecoveryStrategy.MANUAL_INTERVENTION, error, context
        )
        
        assert not success
        assert "Manual intervention required" in message


class TestWorkflowErrorHandler:
    """Test suite for WorkflowErrorHandler class."""
    
    @pytest.fixture
    def error_handler(self):
        """Create a WorkflowErrorHandler instance for testing."""
        return WorkflowErrorHandler()
    
    def test_handle_workflow_error(self, error_handler):
        """Test workflow error handling."""
        test_error = ValueError("Test error message")
        
        recovered, message, strategy = error_handler.handle_workflow_error(
            test_error, operation="test_operation"
        )
        
        # Should determine a strategy and provide a message
        assert isinstance(message, str)
        assert strategy is not None
    
    def test_validate_and_recover(self, error_handler):
        """Test validation and recovery process."""
        # Create a workflow state with some issues
        workflow_state = WorkflowState(
            spec_id="test-spec",
            current_phase=WorkflowPhase.REQUIREMENTS,
            status=WorkflowStatus.DRAFT
        )
        
        validation_result, recovery_actions = error_handler.validate_and_recover(workflow_state)
        
        # Should return validation result and recovery actions
        assert isinstance(validation_result.is_valid, bool)
        assert isinstance(recovery_actions, list)
    
    def test_error_history(self, error_handler):
        """Test error history tracking."""
        test_error = RuntimeError("Test runtime error")
        
        # Handle an error
        error_handler.handle_workflow_error(test_error, operation="test_op")
        
        # Check error history
        history = error_handler.get_error_history()
        assert len(history) >= 1
        assert history[0]["error_type"] == "RuntimeError"
        assert history[0]["operation"] == "test_op"
    
    def test_clear_error_history(self, error_handler):
        """Test clearing error history."""
        test_error = RuntimeError("Test error")
        
        # Add some errors
        error_handler.handle_workflow_error(test_error)
        error_handler.handle_workflow_error(test_error)
        
        # Clear history
        error_handler.clear_error_history()
        
        # Check history is empty
        history = error_handler.get_error_history()
        assert len(history) == 0


class TestWorkflowStateMachine:
    """Test suite for workflow state machine logic."""
    
    def test_workflow_transitions_definition(self):
        """Test that workflow transitions are properly defined."""
        from eco_api.specs.workflow_orchestrator import WorkflowOrchestrator
        
        transitions = WorkflowOrchestrator.VALID_TRANSITIONS
        
        # Should have transitions defined
        assert len(transitions) > 0
        
        # Check specific transitions exist
        transition_pairs = [(t.from_phase, t.to_phase) for t in transitions]
        
        # Forward transitions
        assert (WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN) in transition_pairs
        assert (WorkflowPhase.DESIGN, WorkflowPhase.TASKS) in transition_pairs
        assert (WorkflowPhase.TASKS, WorkflowPhase.EXECUTION) in transition_pairs
        
        # Backward transitions
        assert (WorkflowPhase.DESIGN, WorkflowPhase.REQUIREMENTS) in transition_pairs
        assert (WorkflowPhase.TASKS, WorkflowPhase.DESIGN) in transition_pairs
    
    def test_workflow_state_serialization(self):
        """Test workflow state serialization and deserialization."""
        original_state = WorkflowState(
            spec_id="test-serialization",
            current_phase=WorkflowPhase.DESIGN,
            status=WorkflowStatus.IN_PROGRESS,
            approvals={"requirements": ApprovalStatus.APPROVED},
            metadata={"test_key": "test_value"}
        )
        
        # Serialize
        serialized = original_state.to_dict()
        
        # Deserialize
        restored_state = WorkflowState.from_dict(serialized)
        
        # Compare
        assert restored_state.spec_id == original_state.spec_id
        assert restored_state.current_phase == original_state.current_phase
        assert restored_state.status == original_state.status
        assert restored_state.approvals == original_state.approvals
        assert restored_state.metadata == original_state.metadata


if __name__ == "__main__":
    pytest.main([__file__])