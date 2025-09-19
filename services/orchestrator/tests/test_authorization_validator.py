"""
Tests for the AuthorizationValidator component.

Tests comprehensive server-side authorization validation including
permission checking, role-based access control, audit logging,
and deny-by-default security policies.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, UTC
from unittest.mock import patch, MagicMock

from eco_api.security.authorization_validator import (
    AuthorizationValidator,
    UserContext,
    Permission,
    Role,
    AuthorizationEvent,
    AuthorizationResult,
    create_default_validator,
    create_admin_context,
    create_developer_context
)


class TestUserContext:
    """Test UserContext functionality."""
    
    def test_user_context_creation(self):
        """Test creating a user context with roles and permissions."""
        user_context = UserContext(
            user_id="test_user",
            roles={Role.DEVELOPER},
            permissions={Permission.SPEC_CREATE, Permission.SPEC_READ}
        )
        
        assert user_context.user_id == "test_user"
        assert Role.DEVELOPER in user_context.roles
        assert user_context.has_permission(Permission.SPEC_CREATE)
        assert user_context.has_permission(Permission.SPEC_READ)
        assert not user_context.has_permission(Permission.SYSTEM_ADMIN)
    
    def test_permission_checking(self):
        """Test permission checking methods."""
        user_context = UserContext(
            user_id="test_user",
            permissions={Permission.SPEC_READ, Permission.DOCUMENT_READ}
        )
        
        # Test single permission
        assert user_context.has_permission(Permission.SPEC_READ)
        assert not user_context.has_permission(Permission.SPEC_CREATE)
        
        # Test any permission
        assert user_context.has_any_permission([Permission.SPEC_READ, Permission.SPEC_CREATE])
        assert not user_context.has_any_permission([Permission.SPEC_CREATE, Permission.SYSTEM_ADMIN])
        
        # Test all permissions
        assert user_context.has_all_permissions([Permission.SPEC_READ, Permission.DOCUMENT_READ])
        assert not user_context.has_all_permissions([Permission.SPEC_READ, Permission.SPEC_CREATE])
    
    def test_role_checking(self):
        """Test role checking functionality."""
        user_context = UserContext(
            user_id="test_user",
            roles={Role.DEVELOPER, Role.VIEWER}
        )
        
        assert user_context.has_role(Role.DEVELOPER)
        assert user_context.has_role(Role.VIEWER)
        assert not user_context.has_role(Role.ADMIN)


class TestAuthorizationValidator:
    """Test AuthorizationValidator functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = AuthorizationValidator(workspace_root=self.temp_dir)
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        assert self.validator.workspace_root == Path(self.temp_dir).resolve()
        assert Role.ADMIN in self.validator.role_permissions
        assert Permission.SYSTEM_ADMIN in self.validator.role_permissions[Role.ADMIN]
    
    def test_create_user_context(self):
        """Test creating user context with role-based permissions."""
        user_context = self.validator.create_user_context(
            user_id="test_user",
            roles=["developer"]
        )
        
        assert user_context.user_id == "test_user"
        assert Role.DEVELOPER in user_context.roles
        assert Permission.SPEC_CREATE in user_context.permissions
        assert Permission.SPEC_READ in user_context.permissions
        assert Permission.SYSTEM_ADMIN not in user_context.permissions
    
    def test_create_user_context_multiple_roles(self):
        """Test creating user context with multiple roles."""
        user_context = self.validator.create_user_context(
            user_id="test_user",
            roles=[Role.DEVELOPER, Role.VIEWER]
        )
        
        assert Role.DEVELOPER in user_context.roles
        assert Role.VIEWER in user_context.roles
        
        # Should have permissions from both roles
        assert Permission.SPEC_CREATE in user_context.permissions  # From DEVELOPER
        assert Permission.SPEC_READ in user_context.permissions     # From both
    
    def test_validate_server_side_permissions_authorized(self):
        """Test successful authorization validation."""
        user_context = self.validator.create_user_context(
            user_id="test_user",
            roles=[Role.DEVELOPER]
        )
        
        result = self.validator.validate_server_side_permissions(
            user_context=user_context,
            operation="create_spec",
            permission=Permission.SPEC_CREATE,
            resource="test_spec"
        )
        
        assert result.authorized is True
        assert result.user_context == user_context
        assert result.permission == Permission.SPEC_CREATE
        assert "granted" in result.reason.lower()
        assert result.event is not None
    
    def test_validate_server_side_permissions_denied(self):
        """Test denied authorization validation."""
        user_context = self.validator.create_user_context(
            user_id="test_user",
            roles=[Role.VIEWER]  # Viewer cannot create specs
        )
        
        result = self.validator.validate_server_side_permissions(
            user_context=user_context,
            operation="create_spec",
            permission=Permission.SPEC_CREATE,
            resource="test_spec"
        )
        
        assert result.authorized is False
        assert result.user_context == user_context
        assert result.permission == Permission.SPEC_CREATE
        assert "lacks required permission" in result.reason.lower()
        assert result.event is not None
    
    def test_validate_permissions_no_roles(self):
        """Test authorization validation with no roles assigned."""
        user_context = UserContext(user_id="test_user")  # No roles or permissions
        
        result = self.validator.validate_server_side_permissions(
            user_context=user_context,
            operation="create_spec",
            permission=Permission.SPEC_CREATE
        )
        
        assert result.authorized is False
        assert "no roles assigned" in result.reason.lower()
    
    def test_require_permission_decorator_authorized(self):
        """Test permission decorator with authorized user."""
        user_context = self.validator.create_user_context(
            user_id="test_user",
            roles=[Role.DEVELOPER]
        )
        
        @self.validator.require_permission(Permission.SPEC_CREATE)
        def create_spec(user_context: UserContext, spec_name: str):
            return f"Created spec: {spec_name}"
        
        result = create_spec(user_context, "test_spec")
        assert result == "Created spec: test_spec"
    
    def test_require_permission_decorator_denied(self):
        """Test permission decorator with unauthorized user."""
        user_context = self.validator.create_user_context(
            user_id="test_user",
            roles=[Role.VIEWER]  # Viewer cannot create specs
        )
        
        @self.validator.require_permission(Permission.SPEC_CREATE)
        def create_spec(user_context: UserContext, spec_name: str):
            return f"Created spec: {spec_name}"
        
        with pytest.raises(PermissionError) as exc_info:
            create_spec(user_context, "test_spec")
        
        assert "access denied" in str(exc_info.value).lower()
    
    def test_require_permission_decorator_no_context(self):
        """Test permission decorator with no user context."""
        @self.validator.require_permission(Permission.SPEC_CREATE)
        def create_spec(spec_name: str):
            return f"Created spec: {spec_name}"
        
        with pytest.raises(PermissionError) as exc_info:
            create_spec("test_spec")
        
        assert "no user context" in str(exc_info.value).lower()
    
    def test_add_remove_role_permission(self):
        """Test adding and removing permissions from roles."""
        # Add custom permission to viewer role
        self.validator.add_role_permission(Role.VIEWER, Permission.SPEC_CREATE)
        
        user_context = self.validator.create_user_context(
            user_id="test_user",
            roles=[Role.VIEWER]
        )
        
        assert Permission.SPEC_CREATE in user_context.permissions
        
        # Remove the permission
        self.validator.remove_role_permission(Role.VIEWER, Permission.SPEC_CREATE)
        
        # Create new context to see updated permissions
        user_context_updated = self.validator.create_user_context(
            user_id="test_user",
            roles=[Role.VIEWER]
        )
        
        assert Permission.SPEC_CREATE not in user_context_updated.permissions
    
    @patch('eco_api.security.authorization_validator.logger')
    def test_authorization_error_handling(self, mock_logger):
        """Test error handling during authorization validation."""
        # Create a user context that will cause an error during validation
        user_context = UserContext(user_id="test_user")
        
        # Mock an exception during permission checking
        with patch.object(user_context, 'has_permission', side_effect=Exception("Test error")):
            result = self.validator.validate_server_side_permissions(
                user_context=user_context,
                operation="test_operation",
                permission=Permission.SPEC_CREATE
            )
            
            # Should deny by default on error
            assert result.authorized is False
            assert "authorization validation error" in result.reason.lower()
            mock_logger.error.assert_called()
    
    def test_audit_logging_with_file(self):
        """Test audit logging to file."""
        audit_log_path = Path(self.temp_dir) / "audit.log"
        validator = AuthorizationValidator(
            workspace_root=self.temp_dir,
            audit_log_path=str(audit_log_path)
        )
        
        user_context = validator.create_user_context(
            user_id="test_user",
            roles=[Role.DEVELOPER]
        )
        
        # Perform an authorized operation
        validator.validate_server_side_permissions(
            user_context=user_context,
            operation="test_operation",
            permission=Permission.SPEC_CREATE
        )
        
        # Check that audit log was created and contains entry
        assert audit_log_path.exists()
        log_content = audit_log_path.read_text()
        assert "AUTHORIZATION_GRANTED" in log_content
        assert "test_user" in log_content


class TestAuthorizationEvent:
    """Test AuthorizationEvent functionality."""
    
    def test_authorization_event_creation(self):
        """Test creating authorization events."""
        user_context = UserContext(user_id="test_user")
        
        event = AuthorizationEvent(
            event_id="test_event",
            user_context=user_context,
            operation="test_operation",
            resource="test_resource",
            permission_required=Permission.SPEC_CREATE,
            authorized=True,
            timestamp=datetime.now(UTC)
        )
        
        assert event.event_id == "test_event"
        assert event.user_context == user_context
        assert event.operation == "test_operation"
        assert event.resource == "test_resource"
        assert event.permission_required == Permission.SPEC_CREATE
        assert event.authorized is True
    
    def test_authorization_event_to_dict(self):
        """Test converting authorization event to dictionary."""
        user_context = UserContext(user_id="test_user")
        timestamp = datetime.now(UTC)
        
        event = AuthorizationEvent(
            event_id="test_event",
            user_context=user_context,
            operation="test_operation",
            resource="test_resource",
            permission_required=Permission.SPEC_CREATE,
            authorized=True,
            timestamp=timestamp,
            additional_context={"key": "value"}
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["event_id"] == "test_event"
        assert event_dict["user_id"] == "test_user"
        assert event_dict["operation"] == "test_operation"
        assert event_dict["resource"] == "test_resource"
        assert event_dict["permission_required"] == Permission.SPEC_CREATE.value
        assert event_dict["authorized"] is True
        assert event_dict["timestamp"] == timestamp.isoformat()
        assert event_dict["additional_context"]["key"] == "value"


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_create_default_validator(self):
        """Test creating default validator."""
        with tempfile.TemporaryDirectory() as temp_dir:
            validator = create_default_validator(workspace_root=temp_dir)
            
            assert isinstance(validator, AuthorizationValidator)
            assert validator.workspace_root == Path(temp_dir).resolve()
    
    def test_create_admin_context(self):
        """Test creating admin context."""
        admin_context = create_admin_context("admin_user")
        
        assert admin_context.user_id == "admin_user"
        assert Role.ADMIN in admin_context.roles
        assert Permission.SYSTEM_ADMIN in admin_context.permissions
    
    def test_create_developer_context(self):
        """Test creating developer context."""
        dev_context = create_developer_context("dev_user")
        
        assert dev_context.user_id == "dev_user"
        assert Role.DEVELOPER in dev_context.roles
        assert Permission.SPEC_CREATE in dev_context.permissions
        assert Permission.SYSTEM_ADMIN not in dev_context.permissions


class TestSecurityPolicies:
    """Test security policies and edge cases."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.validator = AuthorizationValidator(workspace_root=self.temp_dir)
    
    def test_deny_by_default_policy(self):
        """Test that operations are denied by default."""
        # Empty user context
        user_context = UserContext(user_id="test_user")
        
        result = self.validator.validate_server_side_permissions(
            user_context=user_context,
            operation="sensitive_operation",
            permission=Permission.SYSTEM_ADMIN
        )
        
        assert result.authorized is False
    
    def test_invalid_role_handling(self):
        """Test handling of invalid roles."""
        user_context = self.validator.create_user_context(
            user_id="test_user",
            roles=["invalid_role", "developer"]  # Mix of invalid and valid
        )
        
        # Should only have developer role
        assert Role.DEVELOPER in user_context.roles
        assert len(user_context.roles) == 1
        
        # Should have developer permissions
        assert Permission.SPEC_CREATE in user_context.permissions
    
    def test_permission_inheritance(self):
        """Test that admin role has all permissions."""
        admin_context = self.validator.create_user_context(
            user_id="admin_user",
            roles=[Role.ADMIN]
        )
        
        # Admin should have all permissions
        for permission in Permission:
            assert permission in admin_context.permissions
    
    def test_guest_role_restrictions(self):
        """Test that guest role has minimal permissions."""
        guest_context = self.validator.create_user_context(
            user_id="guest_user",
            roles=[Role.GUEST]
        )
        
        # Guest should only have read permissions
        assert Permission.SPEC_READ in guest_context.permissions
        assert Permission.DOCUMENT_READ in guest_context.permissions
        
        # Guest should not have write permissions
        assert Permission.SPEC_CREATE not in guest_context.permissions
        assert Permission.SPEC_UPDATE not in guest_context.permissions
        assert Permission.SYSTEM_ADMIN not in guest_context.permissions