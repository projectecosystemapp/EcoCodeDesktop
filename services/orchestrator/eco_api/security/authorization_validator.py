"""
Authorization validation component for server-side security.

This module implements comprehensive server-side authorization validation
to replace client-side authorization checks and ensure security cannot
be bypassed through client manipulation.

Requirements addressed:
- 4.1: Server-side role and permission validation
- 4.2: Replace client-side role checks with server-side validation
- 4.3: Deny unauthorized access and log attempts
- 4.4: Allow authorized operations with proper logging
"""

import logging
from datetime import datetime, UTC
from enum import Enum
from functools import wraps
from typing import Dict, List, Optional, Set, Callable, Any, Union
from dataclasses import dataclass, field
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """System permissions for authorization validation."""
    # Spec management permissions
    SPEC_CREATE = "spec:create"
    SPEC_READ = "spec:read"
    SPEC_UPDATE = "spec:update"
    SPEC_DELETE = "spec:delete"
    
    # Workflow permissions
    WORKFLOW_TRANSITION = "workflow:transition"
    WORKFLOW_APPROVE = "workflow:approve"
    WORKFLOW_EXECUTE = "workflow:execute"
    
    # Document permissions
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    
    # System permissions
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_MONITOR = "system:monitor"


class Role(str, Enum):
    """System roles with predefined permission sets."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"
    GUEST = "guest"


@dataclass
class UserContext:
    """User context for authorization validation."""
    user_id: str
    roles: Set[Role] = field(default_factory=set)
    permissions: Set[Permission] = field(default_factory=set)
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    authenticated_at: Optional[datetime] = None
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions
    
    def has_role(self, role: Role) -> bool:
        """Check if user has specific role."""
        return role in self.roles
    
    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return any(perm in self.permissions for perm in permissions)
    
    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if user has all of the specified permissions."""
        return all(perm in self.permissions for perm in permissions)


@dataclass
class AuthorizationEvent:
    """Authorization event for audit logging."""
    event_id: str
    user_context: UserContext
    operation: str
    resource: Optional[str]
    permission_required: Permission
    authorized: bool
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "event_id": self.event_id,
            "user_id": self.user_context.user_id,
            "operation": self.operation,
            "resource": self.resource,
            "permission_required": self.permission_required.value,
            "authorized": self.authorized,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "additional_context": self.additional_context
        }


class AuthorizationResult:
    """Result of authorization validation."""
    
    def __init__(
        self,
        authorized: bool,
        user_context: UserContext,
        permission: Permission,
        reason: Optional[str] = None,
        event: Optional[AuthorizationEvent] = None
    ):
        self.authorized = authorized
        self.user_context = user_context
        self.permission = permission
        self.reason = reason
        self.event = event


class AuthorizationValidator:
    """
    Server-side authorization validator with comprehensive security controls.
    
    Implements deny-by-default security policy and comprehensive audit logging
    for all authorization events.
    
    Requirements: 4.1, 4.2, 4.3, 4.4
    """
    
    # Default role-permission mappings
    DEFAULT_ROLE_PERMISSIONS = {
        Role.ADMIN: {
            Permission.SPEC_CREATE, Permission.SPEC_READ, Permission.SPEC_UPDATE, Permission.SPEC_DELETE,
            Permission.WORKFLOW_TRANSITION, Permission.WORKFLOW_APPROVE, Permission.WORKFLOW_EXECUTE,
            Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_UPDATE, Permission.DOCUMENT_DELETE,
            Permission.SYSTEM_ADMIN, Permission.SYSTEM_MONITOR
        },
        Role.DEVELOPER: {
            Permission.SPEC_CREATE, Permission.SPEC_READ, Permission.SPEC_UPDATE,
            Permission.WORKFLOW_TRANSITION, Permission.WORKFLOW_EXECUTE,
            Permission.DOCUMENT_CREATE, Permission.DOCUMENT_READ, Permission.DOCUMENT_UPDATE,
            Permission.SYSTEM_MONITOR
        },
        Role.VIEWER: {
            Permission.SPEC_READ,
            Permission.DOCUMENT_READ,
            Permission.SYSTEM_MONITOR
        },
        Role.GUEST: {
            Permission.SPEC_READ,
            Permission.DOCUMENT_READ
        }
    }
    
    def __init__(self, workspace_root: str = ".", audit_log_path: Optional[str] = None):
        """
        Initialize the authorization validator.
        
        Args:
            workspace_root: Root directory of the workspace
            audit_log_path: Path to audit log file (optional)
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.audit_log_path = audit_log_path
        self.role_permissions = self.DEFAULT_ROLE_PERMISSIONS.copy()
        self._setup_audit_logging()
    
    def _setup_audit_logging(self) -> None:
        """Setup audit logging for authorization events."""
        if self.audit_log_path:
            # Create audit log directory if it doesn't exist
            audit_path = Path(self.audit_log_path)
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Setup dedicated audit logger
            self.audit_logger = logging.getLogger("authorization_audit")
            handler = logging.FileHandler(audit_path)
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.audit_logger.addHandler(handler)
            self.audit_logger.setLevel(logging.INFO)
        else:
            self.audit_logger = logger
    
    def validate_server_side_permissions(
        self,
        user_context: UserContext,
        operation: str,
        permission: Permission,
        resource: Optional[str] = None
    ) -> AuthorizationResult:
        """
        Validate server-side permissions for an operation.
        
        Implements deny-by-default security policy where operations are
        denied unless explicitly authorized.
        
        Requirements: 4.1, 4.3, 4.4
        
        Args:
            user_context: User context with roles and permissions
            operation: Operation being performed
            permission: Required permission for the operation
            resource: Optional resource identifier
            
        Returns:
            AuthorizationResult with validation outcome
        """
        try:
            # Generate event ID for tracking
            event_id = f"auth_{int(datetime.now(UTC).timestamp() * 1000000)}"
            
            # Check if user has required permission
            authorized = user_context.has_permission(permission)
            
            # Create authorization event
            auth_event = AuthorizationEvent(
                event_id=event_id,
                user_context=user_context,
                operation=operation,
                resource=resource,
                permission_required=permission,
                authorized=authorized,
                timestamp=datetime.now(UTC),
                ip_address=user_context.ip_address,
                user_agent=user_context.user_agent
            )
            
            # Log authorization event
            self._log_authorization_event(auth_event)
            
            # Determine reason for authorization result
            reason = None
            if not authorized:
                if not user_context.roles:
                    reason = "No roles assigned to user"
                elif not user_context.permissions:
                    reason = "No permissions assigned to user"
                else:
                    reason = f"User lacks required permission: {permission.value}"
            else:
                reason = "Authorization granted"
            
            return AuthorizationResult(
                authorized=authorized,
                user_context=user_context,
                permission=permission,
                reason=reason,
                event=auth_event
            )
            
        except Exception as e:
            logger.error(f"Error validating permissions for operation {operation}: {str(e)}")
            
            # Deny by default on error
            error_event = AuthorizationEvent(
                event_id=f"auth_error_{int(datetime.now(UTC).timestamp() * 1000000)}",
                user_context=user_context,
                operation=operation,
                resource=resource,
                permission_required=permission,
                authorized=False,
                timestamp=datetime.now(UTC),
                additional_context={"error": str(e)}
            )
            
            self._log_authorization_event(error_event)
            
            return AuthorizationResult(
                authorized=False,
                user_context=user_context,
                permission=permission,
                reason=f"Authorization validation error: {str(e)}",
                event=error_event
            )
    
    def require_permission(self, permission: Permission, resource: Optional[str] = None):
        """
        Decorator for protecting sensitive operations with server-side authorization.
        
        Requirements: 4.1, 4.2
        
        Args:
            permission: Required permission for the operation
            resource: Optional resource identifier
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract user context from function arguments
                user_context = self._extract_user_context(args, kwargs)
                
                if not user_context:
                    # No user context provided - deny by default
                    self._log_authorization_failure(
                        operation=func.__name__,
                        permission=permission,
                        resource=resource,
                        reason="No user context provided"
                    )
                    raise PermissionError(f"Access denied: No user context for operation {func.__name__}")
                
                # Validate authorization
                auth_result = self.validate_server_side_permissions(
                    user_context=user_context,
                    operation=func.__name__,
                    permission=permission,
                    resource=resource
                )
                
                if not auth_result.authorized:
                    raise PermissionError(f"Access denied: {auth_result.reason}")
                
                # Execute the protected function
                return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def create_user_context(
        self,
        user_id: str,
        roles: Optional[List[Union[str, Role]]] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserContext:
        """
        Create a user context with appropriate permissions based on roles.
        
        Args:
            user_id: Unique user identifier
            roles: List of user roles
            session_id: Optional session identifier
            ip_address: Optional IP address
            user_agent: Optional user agent string
            
        Returns:
            UserContext with computed permissions
        """
        # Convert string roles to Role enum
        user_roles = set()
        if roles:
            for role in roles:
                if isinstance(role, str):
                    try:
                        user_roles.add(Role(role))
                    except ValueError:
                        logger.warning(f"Invalid role: {role}")
                else:
                    user_roles.add(role)
        
        # Compute permissions based on roles
        permissions = set()
        for role in user_roles:
            role_perms = self.role_permissions.get(role, set())
            permissions.update(role_perms)
        
        return UserContext(
            user_id=user_id,
            roles=user_roles,
            permissions=permissions,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            authenticated_at=datetime.now(UTC)
        )
    
    def add_role_permission(self, role: Role, permission: Permission) -> None:
        """
        Add a permission to a role.
        
        Args:
            role: Role to modify
            permission: Permission to add
        """
        if role not in self.role_permissions:
            self.role_permissions[role] = set()
        self.role_permissions[role].add(permission)
        
        logger.info(f"Added permission {permission.value} to role {role.value}")
    
    def remove_role_permission(self, role: Role, permission: Permission) -> None:
        """
        Remove a permission from a role.
        
        Args:
            role: Role to modify
            permission: Permission to remove
        """
        if role in self.role_permissions:
            self.role_permissions[role].discard(permission)
            logger.info(f"Removed permission {permission.value} from role {role.value}")
    
    def _extract_user_context(self, args: tuple, kwargs: dict) -> Optional[UserContext]:
        """
        Extract user context from function arguments.
        
        Args:
            args: Function positional arguments
            kwargs: Function keyword arguments
            
        Returns:
            UserContext if found, None otherwise
        """
        # Look for user_context in kwargs
        if "user_context" in kwargs:
            return kwargs["user_context"]
        
        # Look for user_context in args (assuming it's typically first or second argument)
        for arg in args:
            if isinstance(arg, UserContext):
                return arg
        
        return None
    
    def _log_authorization_event(self, event: AuthorizationEvent) -> None:
        """
        Log authorization event for audit purposes.
        
        Requirements: 4.3, 4.4
        
        Args:
            event: Authorization event to log
        """
        try:
            log_data = event.to_dict()
            
            if event.authorized:
                self.audit_logger.info(
                    f"AUTHORIZATION_GRANTED: {json.dumps(log_data)}"
                )
            else:
                self.audit_logger.warning(
                    f"AUTHORIZATION_DENIED: {json.dumps(log_data)}"
                )
                
        except Exception as e:
            logger.error(f"Error logging authorization event: {str(e)}")
    
    def _log_authorization_failure(
        self,
        operation: str,
        permission: Permission,
        resource: Optional[str] = None,
        reason: str = "Unknown"
    ) -> None:
        """
        Log authorization failure when no user context is available.
        
        Args:
            operation: Operation that was attempted
            permission: Required permission
            resource: Optional resource identifier
            reason: Reason for failure
        """
        try:
            log_data = {
                "event_type": "AUTHORIZATION_FAILURE",
                "operation": operation,
                "permission_required": permission.value,
                "resource": resource,
                "reason": reason,
                "timestamp": datetime.now(UTC).isoformat()
            }
            
            self.audit_logger.error(
                f"AUTHORIZATION_FAILURE: {json.dumps(log_data)}"
            )
            
        except Exception as e:
            logger.error(f"Error logging authorization failure: {str(e)}")


# Convenience functions for common authorization patterns
def create_default_validator(workspace_root: str = ".") -> AuthorizationValidator:
    """
    Create a default authorization validator with standard configuration.
    
    Args:
        workspace_root: Root directory of the workspace
        
    Returns:
        Configured AuthorizationValidator instance
    """
    audit_log_path = Path(workspace_root) / ".kiro" / "logs" / "authorization.log"
    return AuthorizationValidator(
        workspace_root=workspace_root,
        audit_log_path=str(audit_log_path)
    )


def create_admin_context(user_id: str = "admin") -> UserContext:
    """
    Create an admin user context for testing or system operations.
    
    Args:
        user_id: User identifier
        
    Returns:
        UserContext with admin privileges
    """
    validator = create_default_validator()
    return validator.create_user_context(
        user_id=user_id,
        roles=[Role.ADMIN]
    )


def create_developer_context(user_id: str) -> UserContext:
    """
    Create a developer user context.
    
    Args:
        user_id: User identifier
        
    Returns:
        UserContext with developer privileges
    """
    validator = create_default_validator()
    return validator.create_user_context(
        user_id=user_id,
        roles=[Role.DEVELOPER]
    )