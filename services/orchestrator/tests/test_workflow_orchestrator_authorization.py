"""
Tests for WorkflowOrchestrator authorization integration.

Tests server-side authorization validation for workflow operations
including spec creation, transitions, approvals, and access control.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from eco_api.specs.workflow_orchestrator import WorkflowOrchestrator, WorkflowPhase
from eco_api.specs.models import ValidationResult, ValidationError, FileOperationResult
from eco_api.security.authorization_validator import (
    AuthorizationValidator, UserContext, Permission, Role,
    create_admin_context, create_developer_context
)


class TestWorkflowOrchestratorAuthorization:
    """Test authorization integration in WorkflowOrchestrator."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.auth_validator = AuthorizationValidator(workspace_root=self.temp_dir)
        self.orchestrator = WorkflowOrchestrator(
            workspace_root=self.temp_dir,
            authorization_validator=self.auth_validator
        )
        
        # Create test user contexts
        self.admin_context = create_admin_context("admin_user")
        self.developer_context = create_developer_context("dev_user")
        self.viewer_context = self.auth_validator.create_user_context(
            user_id="viewer_user",
            roles=[Role.VIEWER]
        )
    
    def test_create_spec_workflow_authorized_admin(self):
        """Test spec creation with authorized admin user."""
        workflow_state, result = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature for admin",
            feature_name="admin-test-feature",
            user_context=self.admin_context
        )
        
        assert result.success is True
        assert workflow_state is not None
        assert workflow_state.spec_id == "admin-test-feature"
        assert workflow_state.metadata["created_by"] == "admin_user"
        assert "admin" in workflow_state.metadata["created_by_roles"]
    
    def test_create_spec_workflow_authorized_developer(self):
        """Test spec creation with authorized developer user."""
        workflow_state, result = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature for developer",
            feature_name="dev-test-feature",
            user_context=self.developer_context
        )
        
        assert result.success is True
        assert workflow_state is not None
        assert workflow_state.spec_id == "dev-test-feature"
        assert workflow_state.metadata["created_by"] == "dev_user"
        assert "developer" in workflow_state.metadata["created_by_roles"]
    
    def test_create_spec_workflow_unauthorized_viewer(self):
        """Test spec creation denied for viewer user."""
        workflow_state, result = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature for viewer",
            feature_name="viewer-test-feature",
            user_context=self.viewer_context
        )
        
        assert result.success is False
        assert workflow_state is None
        assert result.error_code == "AUTHORIZATION_DENIED"
        assert "access denied" in result.message.lower()
    
    def test_create_spec_workflow_no_user_context(self):
        """Test spec creation denied without user context."""
        workflow_state, result = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature without context",
            feature_name="no-context-feature"
        )
        
        assert result.success is False
        assert workflow_state is None
        assert result.error_code == "MISSING_USER_CONTEXT"
        assert "user context required" in result.message.lower()
    
    def test_transition_workflow_authorized(self):
        """Test workflow transition with authorized user."""
        # First create a workflow
        workflow_state, _ = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature",
            feature_name="transition-test",
            user_context=self.developer_context
        )
        
        # Mock the validation to avoid file system operations
        with patch.object(self.orchestrator, '_validate_phase_requirements') as mock_validate:
            mock_validate.return_value = []  # No validation errors
            
            # Transition workflow
            updated_state, validation = self.orchestrator.transition_workflow(
                spec_id="transition-test",
                target_phase=WorkflowPhase.DESIGN,
                approval=True,
                user_context=self.developer_context
            )
            
            assert validation.is_valid is True
            assert updated_state is not None
            assert updated_state.current_phase == WorkflowPhase.DESIGN
            
            # Check transition metadata includes user information
            transition_keys = [key for key in updated_state.metadata.keys() if key.startswith("transition_")]
            assert len(transition_keys) > 0
            
            latest_transition = updated_state.metadata[transition_keys[-1]]
            assert latest_transition["transitioned_by"] == "dev_user"
            assert "developer" in latest_transition["user_roles"]
    
    def test_transition_workflow_unauthorized(self):
        """Test workflow transition denied for unauthorized user."""
        # First create a workflow as admin
        workflow_state, _ = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature",
            feature_name="transition-unauthorized-test",
            user_context=self.admin_context
        )
        
        # Try to transition as viewer (unauthorized)
        updated_state, validation = self.orchestrator.transition_workflow(
            spec_id="transition-unauthorized-test",
            target_phase=WorkflowPhase.DESIGN,
            approval=True,
            user_context=self.viewer_context
        )
        
        assert validation.is_valid is False
        assert updated_state is None
        assert any(error.code == "AUTHORIZATION_DENIED" for error in validation.errors)
    
    def test_transition_workflow_no_user_context(self):
        """Test workflow transition denied without user context."""
        # First create a workflow
        workflow_state, _ = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature",
            feature_name="transition-no-context-test",
            user_context=self.admin_context
        )
        
        # Try to transition without user context
        updated_state, validation = self.orchestrator.transition_workflow(
            spec_id="transition-no-context-test",
            target_phase=WorkflowPhase.DESIGN,
            approval=True
        )
        
        assert validation.is_valid is False
        assert updated_state is None
        assert any(error.code == "MISSING_USER_CONTEXT" for error in validation.errors)
    
    def test_approve_phase_authorized(self):
        """Test phase approval with authorized user."""
        # First create a workflow
        workflow_state, _ = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature",
            feature_name="approve-test",
            user_context=self.developer_context
        )
        
        # Approve phase with admin user (has approval permission)
        updated_state, validation = self.orchestrator.approve_phase(
            spec_id="approve-test",
            phase=WorkflowPhase.REQUIREMENTS,
            approved=True,
            feedback="Looks good!",
            user_context=self.admin_context
        )
        
        assert validation.is_valid is True
        assert updated_state is not None
        assert updated_state.metadata["requirements_approved_by"] == "admin_user"
        assert "admin" in updated_state.metadata["requirements_approved_by_roles"]
        assert updated_state.metadata["requirements_feedback"] == "Looks good!"
    
    def test_approve_phase_unauthorized(self):
        """Test phase approval denied for unauthorized user."""
        # First create a workflow
        workflow_state, _ = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature",
            feature_name="approve-unauthorized-test",
            user_context=self.admin_context
        )
        
        # Try to approve as viewer (unauthorized)
        updated_state, validation = self.orchestrator.approve_phase(
            spec_id="approve-unauthorized-test",
            phase=WorkflowPhase.REQUIREMENTS,
            approved=True,
            user_context=self.viewer_context
        )
        
        assert validation.is_valid is False
        assert updated_state is None
        assert any(error.code == "AUTHORIZATION_DENIED" for error in validation.errors)
    
    def test_approve_phase_no_user_context(self):
        """Test phase approval denied without user context."""
        # First create a workflow
        workflow_state, _ = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature",
            feature_name="approve-no-context-test",
            user_context=self.admin_context
        )
        
        # Try to approve without user context
        updated_state, validation = self.orchestrator.approve_phase(
            spec_id="approve-no-context-test",
            phase=WorkflowPhase.REQUIREMENTS,
            approved=True
        )
        
        assert validation.is_valid is False
        assert updated_state is None
        assert any(error.code == "MISSING_USER_CONTEXT" for error in validation.errors)
    
    def test_get_workflow_state_authorized(self):
        """Test getting workflow state with authorized user."""
        # First create a workflow
        workflow_state, _ = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature",
            feature_name="get-state-test",
            user_context=self.developer_context
        )
        
        # Get workflow state with authorized user
        retrieved_state = self.orchestrator.get_workflow_state(
            spec_id="get-state-test",
            user_context=self.developer_context
        )
        
        assert retrieved_state is not None
        assert retrieved_state.spec_id == "get-state-test"
    
    def test_get_workflow_state_unauthorized(self):
        """Test getting workflow state denied for unauthorized user."""
        # First create a workflow
        workflow_state, _ = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature",
            feature_name="get-state-unauthorized-test",
            user_context=self.admin_context
        )
        
        # Create a user with no permissions
        no_permission_context = UserContext(user_id="no_permission_user")
        
        # Try to get workflow state with unauthorized user
        retrieved_state = self.orchestrator.get_workflow_state(
            spec_id="get-state-unauthorized-test",
            user_context=no_permission_context
        )
        
        assert retrieved_state is None
    
    def test_list_workflows_authorized(self):
        """Test listing workflows with authorized user."""
        # Create some workflows
        self.orchestrator.create_spec_workflow(
            feature_idea="Test feature 1",
            feature_name="list-test-1",
            user_context=self.admin_context
        )
        self.orchestrator.create_spec_workflow(
            feature_idea="Test feature 2",
            feature_name="list-test-2",
            user_context=self.developer_context
        )
        
        # Mock the file manager to return our test specs
        with patch.object(self.orchestrator.file_manager, 'list_existing_specs') as mock_list:
            mock_list.return_value = []  # Simplified for test
            
            # List workflows with authorized user
            workflows = self.orchestrator.list_workflows(user_context=self.developer_context)
            
            # Should return empty list but not fail authorization
            assert isinstance(workflows, list)
    
    def test_list_workflows_unauthorized(self):
        """Test listing workflows denied for unauthorized user."""
        # Create a user with no permissions
        no_permission_context = UserContext(user_id="no_permission_user")
        
        # Try to list workflows with unauthorized user
        workflows = self.orchestrator.list_workflows(user_context=no_permission_context)
        
        # Should return empty list due to authorization failure
        assert workflows == []
    
    @patch('eco_api.specs.workflow_orchestrator.logger')
    def test_security_logging(self, mock_logger):
        """Test that security events are properly logged."""
        # Test unauthorized spec creation
        self.orchestrator.create_spec_workflow(
            feature_idea="Test feature",
            feature_name="security-log-test",
            user_context=self.viewer_context
        )
        
        # Check that warning was logged
        mock_logger.warning.assert_called()
        warning_calls = [call for call in mock_logger.warning.call_args_list 
                        if "Unauthorized spec creation attempt" in str(call)]
        assert len(warning_calls) > 0
    
    def test_backward_compatibility_without_user_context(self):
        """Test that methods still work without user context for backward compatibility."""
        # Create a workflow without user context (should fail)
        workflow_state, result = self.orchestrator.create_spec_workflow(
            feature_idea="Test feature"
        )
        
        assert result.success is False
        assert result.error_code == "MISSING_USER_CONTEXT"
        
        # But getting workflow state should work (with warning)
        with patch('eco_api.specs.workflow_orchestrator.logger') as mock_logger:
            # First create a workflow properly
            workflow_state, _ = self.orchestrator.create_spec_workflow(
                feature_idea="Test feature",
                feature_name="backward-compat-test",
                user_context=self.admin_context
            )
            
            # Then access without user context
            retrieved_state = self.orchestrator.get_workflow_state("backward-compat-test")
            
            # Should work but log warning
            assert retrieved_state is not None
            mock_logger.warning.assert_called()
    
    def test_authorization_validator_integration(self):
        """Test that the orchestrator properly integrates with the authorization validator."""
        # Verify that the orchestrator has an authorization validator
        assert self.orchestrator.auth_validator is not None
        assert isinstance(self.orchestrator.auth_validator, AuthorizationValidator)
        
        # Verify that it uses the provided validator
        custom_validator = AuthorizationValidator(workspace_root=self.temp_dir)
        custom_orchestrator = WorkflowOrchestrator(
            workspace_root=self.temp_dir,
            authorization_validator=custom_validator
        )
        
        assert custom_orchestrator.auth_validator is custom_validator
    
    def test_default_authorization_validator_creation(self):
        """Test that a default authorization validator is created when none is provided."""
        default_orchestrator = WorkflowOrchestrator(workspace_root=self.temp_dir)
        
        assert default_orchestrator.auth_validator is not None
        assert isinstance(default_orchestrator.auth_validator, AuthorizationValidator)


class TestAuthorizationAuditTrail:
    """Test authorization audit trail functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create authorization validator with audit logging
        audit_log_path = Path(self.temp_dir) / "audit.log"
        self.auth_validator = AuthorizationValidator(
            workspace_root=self.temp_dir,
            audit_log_path=str(audit_log_path)
        )
        
        self.orchestrator = WorkflowOrchestrator(
            workspace_root=self.temp_dir,
            authorization_validator=self.auth_validator
        )
        
        self.admin_context = create_admin_context("audit_admin")
        self.audit_log_path = audit_log_path
    
    def test_audit_trail_creation(self):
        """Test that audit trail is created for authorized operations."""
        # Perform an authorized operation
        self.orchestrator.create_spec_workflow(
            feature_idea="Audit test feature",
            feature_name="audit-test",
            user_context=self.admin_context
        )
        
        # Check that audit log was created
        assert self.audit_log_path.exists()
        
        # Check audit log content
        log_content = self.audit_log_path.read_text()
        assert "AUTHORIZATION_GRANTED" in log_content
        assert "audit_admin" in log_content
        assert "create_spec_workflow" in log_content
    
    def test_audit_trail_unauthorized_operations(self):
        """Test that audit trail captures unauthorized operations."""
        viewer_context = self.auth_validator.create_user_context(
            user_id="audit_viewer",
            roles=[Role.VIEWER]
        )
        
        # Perform an unauthorized operation
        self.orchestrator.create_spec_workflow(
            feature_idea="Unauthorized audit test",
            feature_name="unauthorized-audit-test",
            user_context=viewer_context
        )
        
        # Check audit log content
        log_content = self.audit_log_path.read_text()
        assert "AUTHORIZATION_DENIED" in log_content
        assert "audit_viewer" in log_content
        assert "create_spec_workflow" in log_content