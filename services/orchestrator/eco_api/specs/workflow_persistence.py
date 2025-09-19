"""
Workflow persistence and recovery mechanisms.

This module handles serialization, deserialization, and recovery of workflow
states, providing robust persistence with versioning and recovery capabilities
for interrupted sessions.

Requirements addressed:
- 8.1: Workflow state serialization and deserialization
- 8.6: Workflow recovery mechanisms for interrupted sessions
- 8.10, 8.11: Workflow metadata management and versioning
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from uuid import uuid4

from .models import (
    WorkflowPhase, WorkflowStatus, ValidationResult, ValidationError,
    ValidationWarning, FileOperationResult
)
from ..security.path_validator import PathValidator, PathValidationError, SecurityLevel


logger = logging.getLogger(__name__)


class WorkflowVersion:
    """Represents a version of a workflow state."""
    
    def __init__(
        self,
        version_id: str,
        timestamp: datetime,
        data: Dict[str, Any],
        description: Optional[str] = None
    ):
        self.version_id = version_id
        self.timestamp = timestamp
        self.data = data
        self.description = description or f"Version {version_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version_id": self.version_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowVersion':
        """Create from dictionary."""
        return cls(
            version_id=data["version_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            data=data["data"],
            description=data.get("description")
        )


class WorkflowMetadata:
    """Metadata for workflow persistence."""
    
    def __init__(
        self,
        spec_id: str,
        created_at: datetime,
        updated_at: datetime,
        version: str = "1.0.0",
        schema_version: str = "1.0",
        checksum: Optional[str] = None
    ):
        self.spec_id = spec_id
        self.created_at = created_at
        self.updated_at = updated_at
        self.version = version
        self.schema_version = schema_version
        self.checksum = checksum
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "spec_id": self.spec_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "schema_version": self.schema_version,
            "checksum": self.checksum
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowMetadata':
        """Create from dictionary."""
        return cls(
            spec_id=data["spec_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", "1.0.0"),
            schema_version=data.get("schema_version", "1.0"),
            checksum=data.get("checksum")
        )


class WorkflowPersistenceManager:
    """
    Manages workflow state persistence and recovery.
    
    Provides robust serialization, versioning, and recovery mechanisms
    for workflow states with support for interrupted sessions.
    
    Requirements: 8.1, 8.6, 8.10, 8.11
    """
    
    WORKFLOW_STATE_FILE = ".workflow-state.json"
    WORKFLOW_METADATA_FILE = ".workflow-metadata.json"
    WORKFLOW_VERSIONS_DIR = ".workflow-versions"
    WORKFLOW_BACKUP_DIR = ".workflow-backups"
    
    MAX_VERSIONS = 10  # Keep last 10 versions
    MAX_BACKUPS = 5    # Keep last 5 backups
    
    def __init__(self, workspace_root: str = "."):
        """
        Initialize the persistence manager.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.specs_dir = self.workspace_root / ".kiro" / "specs"
        
        # Initialize path validator for security
        self.path_validator = PathValidator(
            workspace_root=self.workspace_root,
            security_level=SecurityLevel.STRICT,
            allowed_extensions=['.json'],  # Only allow JSON files for workflow persistence
            max_path_length=260,
            max_component_length=255
        )
    
    def _validate_and_secure_path(self, path: Union[str, Path], allow_creation: bool = False) -> FileOperationResult:
        """
        Validate and secure a path using PathValidator.
        
        Args:
            path: Path to validate
            allow_creation: Whether to allow paths that don't exist yet
            
        Returns:
            FileOperationResult with validation status and secure path
        """
        try:
            validation_result = self.path_validator.validate_path(path, allow_creation=allow_creation)
            
            if not validation_result.is_valid:
                return FileOperationResult(
                    success=False,
                    message=f"Path validation failed: {', '.join(validation_result.errors)}",
                    error_code="PATH_VALIDATION_ERROR"
                )
            
            # Get the secure path
            secure_path = self.path_validator.get_safe_path(path, relative_to_workspace=True)
            
            return FileOperationResult(
                success=True,
                message="Path validation successful",
                path=str(secure_path)
            )
            
        except PathValidationError as e:
            return FileOperationResult(
                success=False,
                message=f"Path security error: {str(e)}",
                error_code="PATH_SECURITY_ERROR"
            )
        except Exception as e:
            return FileOperationResult(
                success=False,
                message=f"Unexpected path validation error: {str(e)}",
                error_code="PATH_VALIDATION_UNEXPECTED_ERROR"
            )
    
    def serialize_workflow_state(self, workflow_state: Any) -> Dict[str, Any]:
        """
        Serialize workflow state to dictionary.
        
        Requirements: 8.1 - Workflow state serialization
        
        Args:
            workflow_state: The workflow state object to serialize
            
        Returns:
            Serialized workflow state as dictionary
        """
        try:
            if hasattr(workflow_state, 'to_dict'):
                return workflow_state.to_dict()
            
            # Fallback serialization for basic objects
            return {
                "spec_id": getattr(workflow_state, 'spec_id', ''),
                "current_phase": getattr(workflow_state, 'current_phase', WorkflowPhase.REQUIREMENTS).value,
                "status": getattr(workflow_state, 'status', WorkflowStatus.DRAFT).value,
                "approvals": {
                    k: v.value if hasattr(v, 'value') else v
                    for k, v in getattr(workflow_state, 'approvals', {}).items()
                },
                "metadata": getattr(workflow_state, 'metadata', {}),
                "created_at": getattr(workflow_state, 'created_at', datetime.utcnow()).isoformat(),
                "updated_at": getattr(workflow_state, 'updated_at', datetime.utcnow()).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error serializing workflow state: {str(e)}")
            raise ValueError(f"Failed to serialize workflow state: {str(e)}")
    
    def deserialize_workflow_state(self, data: Dict[str, Any]) -> Any:
        """
        Deserialize workflow state from dictionary.
        
        Requirements: 8.1 - Workflow state deserialization
        
        Args:
            data: Serialized workflow state data
            
        Returns:
            Deserialized workflow state object
        """
        try:
            # Import here to avoid circular imports
            from .workflow_orchestrator import WorkflowState, ApprovalStatus
            
            return WorkflowState.from_dict(data)
            
        except Exception as e:
            logger.error(f"Error deserializing workflow state: {str(e)}")
            raise ValueError(f"Failed to deserialize workflow state: {str(e)}")
    
    def save_workflow_state(
        self,
        workflow_state: Any,
        create_version: bool = True,
        description: Optional[str] = None
    ) -> FileOperationResult:
        """
        Save workflow state with versioning support.
        
        Requirements: 8.1, 8.11 - Workflow state persistence and versioning
        
        Args:
            workflow_state: The workflow state to save
            create_version: Whether to create a version backup
            description: Optional description for the version
            
        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            spec_id = getattr(workflow_state, 'spec_id', '')
            if not spec_id:
                return FileOperationResult(
                    success=False,
                    message="Workflow state missing spec_id",
                    error_code="INVALID_WORKFLOW_STATE"
                )
            
            # Validate and secure the spec directory path
            spec_dir_path = self.path_validator.secure_join(".kiro", "specs", spec_id)
            spec_dir_validation = self._validate_and_secure_path(spec_dir_path, allow_creation=False)
            if not spec_dir_validation.success:
                return spec_dir_validation
            
            spec_dir = Path(spec_dir_validation.path)
            if not spec_dir.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Spec directory does not exist: {spec_dir}",
                    error_code="SPEC_NOT_FOUND"
                )
            
            # Serialize workflow state
            serialized_data = self.serialize_workflow_state(workflow_state)
            
            # Create version backup if requested
            if create_version:
                version_result = self._create_version_backup(spec_id, serialized_data, description)
                if not version_result.success:
                    logger.warning(f"Failed to create version backup: {version_result.message}")
            
            # Validate and secure the state file path
            state_file_path = self.path_validator.secure_join(".kiro", "specs", spec_id, self.WORKFLOW_STATE_FILE)
            state_file_validation = self._validate_and_secure_path(state_file_path, allow_creation=True)
            if not state_file_validation.success:
                return state_file_validation
            
            state_file = Path(state_file_validation.path)
            
            # Create backup of current state
            if state_file.exists():
                backup_result = self._create_backup(spec_id, state_file)
                if not backup_result.success:
                    logger.warning(f"Failed to create backup: {backup_result.message}")
            
            # Write new state
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(serialized_data, f, indent=2, ensure_ascii=False)
            
            # Update metadata
            metadata_result = self._update_workflow_metadata(spec_id, serialized_data)
            if not metadata_result.success:
                logger.warning(f"Failed to update metadata: {metadata_result.message}")
            
            # Cleanup old versions and backups
            self._cleanup_old_versions(spec_id)
            self._cleanup_old_backups(spec_id)
            
            return FileOperationResult(
                success=True,
                message=f"Workflow state saved successfully for {spec_id}",
                path=str(state_file)
            )
            
        except PathValidationError as e:
            logger.error(f"Path validation error saving workflow state: {str(e)}")
            return FileOperationResult(
                success=False,
                message=f"Path security error: {str(e)}",
                error_code="PATH_SECURITY_ERROR"
            )
        except Exception as e:
            logger.error(f"Error saving workflow state: {str(e)}")
            return FileOperationResult(
                success=False,
                message=f"Failed to save workflow state: {str(e)}",
                error_code="SAVE_ERROR"
            )
    
    def load_workflow_state(self, spec_id: str) -> Tuple[Optional[Any], FileOperationResult]:
        """
        Load workflow state with integrity checking.
        
        Requirements: 8.1, 8.6 - Workflow state loading and integrity validation
        
        Args:
            spec_id: The spec identifier
            
        Returns:
            Tuple of (workflow_state or None, FileOperationResult)
        """
        try:
            # Validate and secure the state file path
            state_file_path = self.path_validator.secure_join(".kiro", "specs", spec_id, self.WORKFLOW_STATE_FILE)
            state_file_validation = self._validate_and_secure_path(state_file_path, allow_creation=False)
            if not state_file_validation.success:
                return None, state_file_validation
            
            state_file = Path(state_file_validation.path)
            
            if not state_file.exists():
                return None, FileOperationResult(
                    success=False,
                    message=f"Workflow state file not found: {state_file}",
                    error_code="STATE_NOT_FOUND"
                )
            
            # Load state data
            with open(state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # Validate integrity
            integrity_result = self._validate_state_integrity(spec_id, state_data)
            if not integrity_result.is_valid:
                # Attempt recovery
                recovery_result = self.recover_workflow_state(spec_id)
                if recovery_result[0]:
                    return recovery_result
                
                return None, FileOperationResult(
                    success=False,
                    message=f"Workflow state integrity check failed: {integrity_result.errors[0].message}",
                    error_code="INTEGRITY_ERROR"
                )
            
            # Deserialize workflow state
            workflow_state = self.deserialize_workflow_state(state_data)
            
            return workflow_state, FileOperationResult(
                success=True,
                message=f"Workflow state loaded successfully for {spec_id}",
                path=str(state_file)
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error loading workflow state: {str(e)}")
            # Attempt recovery from backup
            recovery_result = self.recover_workflow_state(spec_id)
            if recovery_result[0]:
                return recovery_result
            
            return None, FileOperationResult(
                success=False,
                message=f"Invalid JSON in workflow state file: {str(e)}",
                error_code="JSON_ERROR"
            )
        except PathValidationError as e:
            logger.error(f"Path validation error loading workflow state: {str(e)}")
            return None, FileOperationResult(
                success=False,
                message=f"Path security error: {str(e)}",
                error_code="PATH_SECURITY_ERROR"
            )
        except Exception as e:
            logger.error(f"Error loading workflow state: {str(e)}")
            return None, FileOperationResult(
                success=False,
                message=f"Failed to load workflow state: {str(e)}",
                error_code="LOAD_ERROR"
            )
    
    def recover_workflow_state(self, spec_id: str) -> Tuple[Optional[Any], FileOperationResult]:
        """
        Recover workflow state from backups or versions.
        
        Requirements: 8.6, 8.10 - Workflow recovery mechanisms for interrupted sessions
        
        Args:
            spec_id: The spec identifier
            
        Returns:
            Tuple of (recovered_workflow_state or None, FileOperationResult)
        """
        try:
            spec_dir = self.specs_dir / spec_id
            
            # Try to recover from most recent backup
            backup_recovery = self._recover_from_backup(spec_id)
            if backup_recovery[0]:
                logger.info(f"Recovered workflow state from backup for {spec_id}")
                return backup_recovery
            
            # Try to recover from most recent version
            version_recovery = self._recover_from_version(spec_id)
            if version_recovery[0]:
                logger.info(f"Recovered workflow state from version for {spec_id}")
                return version_recovery
            
            # Try to reconstruct from spec metadata
            metadata_recovery = self._recover_from_metadata(spec_id)
            if metadata_recovery[0]:
                logger.info(f"Recovered workflow state from metadata for {spec_id}")
                return metadata_recovery
            
            return None, FileOperationResult(
                success=False,
                message=f"Unable to recover workflow state for {spec_id}",
                error_code="RECOVERY_FAILED"
            )
            
        except Exception as e:
            logger.error(f"Error during workflow recovery: {str(e)}")
            return None, FileOperationResult(
                success=False,
                message=f"Recovery process failed: {str(e)}",
                error_code="RECOVERY_ERROR"
            )
    
    def list_workflow_versions(self, spec_id: str) -> List[WorkflowVersion]:
        """
        List available versions for a workflow.
        
        Requirements: 8.11 - Workflow metadata management and versioning
        
        Args:
            spec_id: The spec identifier
            
        Returns:
            List of available workflow versions
        """
        try:
            versions_dir = self.specs_dir / spec_id / self.WORKFLOW_VERSIONS_DIR
            if not versions_dir.exists():
                return []
            
            versions = []
            for version_file in versions_dir.glob("*.json"):
                try:
                    with open(version_file, 'r', encoding='utf-8') as f:
                        version_data = json.load(f)
                    
                    version = WorkflowVersion.from_dict(version_data)
                    versions.append(version)
                    
                except Exception as e:
                    logger.warning(f"Failed to load version {version_file}: {str(e)}")
                    continue
            
            # Sort by timestamp, newest first
            return sorted(versions, key=lambda v: v.timestamp, reverse=True)
            
        except Exception as e:
            logger.error(f"Error listing workflow versions: {str(e)}")
            return []
    
    def restore_workflow_version(self, spec_id: str, version_id: str) -> Tuple[Optional[Any], FileOperationResult]:
        """
        Restore a specific workflow version.
        
        Requirements: 8.10, 8.11 - Workflow recovery and versioning
        
        Args:
            spec_id: The spec identifier
            version_id: The version identifier to restore
            
        Returns:
            Tuple of (restored_workflow_state or None, FileOperationResult)
        """
        try:
            versions_dir = self.specs_dir / spec_id / self.WORKFLOW_VERSIONS_DIR
            version_file = versions_dir / f"{version_id}.json"
            
            if not version_file.exists():
                return None, FileOperationResult(
                    success=False,
                    message=f"Version {version_id} not found for spec {spec_id}",
                    error_code="VERSION_NOT_FOUND"
                )
            
            # Load version data
            with open(version_file, 'r', encoding='utf-8') as f:
                version_data = json.load(f)
            
            version = WorkflowVersion.from_dict(version_data)
            
            # Deserialize workflow state
            workflow_state = self.deserialize_workflow_state(version.data)
            
            # Save as current state (with backup)
            save_result = self.save_workflow_state(
                workflow_state,
                create_version=True,
                description=f"Restored from version {version_id}"
            )
            
            if not save_result.success:
                return None, save_result
            
            return workflow_state, FileOperationResult(
                success=True,
                message=f"Successfully restored version {version_id} for spec {spec_id}",
                path=str(version_file)
            )
            
        except Exception as e:
            logger.error(f"Error restoring workflow version: {str(e)}")
            return None, FileOperationResult(
                success=False,
                message=f"Failed to restore version: {str(e)}",
                error_code="RESTORE_ERROR"
            )
    
    def _create_version_backup(
        self,
        spec_id: str,
        state_data: Dict[str, Any],
        description: Optional[str] = None
    ) -> FileOperationResult:
        """Create a versioned backup of workflow state."""
        try:
            # Validate and secure the versions directory path
            versions_dir_path = self.path_validator.secure_join(".kiro", "specs", spec_id, self.WORKFLOW_VERSIONS_DIR)
            versions_dir_validation = self._validate_and_secure_path(versions_dir_path, allow_creation=True)
            if not versions_dir_validation.success:
                return versions_dir_validation
            
            versions_dir = Path(versions_dir_validation.path)
            versions_dir.mkdir(exist_ok=True)
            
            # Generate version ID
            version_id = str(uuid4())[:8]
            timestamp = datetime.utcnow()
            
            # Create version object
            version = WorkflowVersion(
                version_id=version_id,
                timestamp=timestamp,
                data=state_data,
                description=description or f"Auto-version {version_id}"
            )
            
            # Validate and secure the version file path
            version_file_path = self.path_validator.secure_join(".kiro", "specs", spec_id, self.WORKFLOW_VERSIONS_DIR, f"{version_id}.json")
            version_file_validation = self._validate_and_secure_path(version_file_path, allow_creation=True)
            if not version_file_validation.success:
                return version_file_validation
            
            # Save version
            version_file = Path(version_file_validation.path)
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(version.to_dict(), f, indent=2, ensure_ascii=False)
            
            return FileOperationResult(
                success=True,
                message=f"Version backup created: {version_id}",
                path=str(version_file)
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                message=f"Failed to create version backup: {str(e)}",
                error_code="VERSION_BACKUP_ERROR"
            )
    
    def _create_backup(self, spec_id: str, source_file: Path) -> FileOperationResult:
        """Create a backup of the current state file."""
        try:
            # Validate and secure the backups directory path
            backups_dir_path = self.path_validator.secure_join(".kiro", "specs", spec_id, self.WORKFLOW_BACKUP_DIR)
            backups_dir_validation = self._validate_and_secure_path(backups_dir_path, allow_creation=True)
            if not backups_dir_validation.success:
                return backups_dir_validation
            
            backups_dir = Path(backups_dir_validation.path)
            backups_dir.mkdir(exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_file = backups_dir / f"workflow-state-{timestamp}.json"
            
            # Copy file
            shutil.copy2(source_file, backup_file)
            
            return FileOperationResult(
                success=True,
                message=f"Backup created: {backup_file.name}",
                path=str(backup_file)
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                message=f"Failed to create backup: {str(e)}",
                error_code="BACKUP_ERROR"
            )
    
    def _validate_state_integrity(self, spec_id: str, state_data: Dict[str, Any]) -> ValidationResult:
        """Validate the integrity of workflow state data."""
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            # Check required fields
            required_fields = ["spec_id", "current_phase", "status"]
            for field in required_fields:
                if field not in state_data:
                    errors.append(ValidationError(
                        code="MISSING_REQUIRED_FIELD",
                        message=f"Required field missing: {field}",
                        field=field
                    ))
            
            # Validate spec_id matches
            if state_data.get("spec_id") != spec_id:
                errors.append(ValidationError(
                    code="SPEC_ID_MISMATCH",
                    message=f"Spec ID mismatch: expected {spec_id}, got {state_data.get('spec_id')}",
                    field="spec_id"
                ))
            
            # Validate enum values
            try:
                WorkflowPhase(state_data.get("current_phase", ""))
            except ValueError:
                errors.append(ValidationError(
                    code="INVALID_WORKFLOW_PHASE",
                    message=f"Invalid workflow phase: {state_data.get('current_phase')}",
                    field="current_phase"
                ))
            
            try:
                WorkflowStatus(state_data.get("status", ""))
            except ValueError:
                errors.append(ValidationError(
                    code="INVALID_WORKFLOW_STATUS",
                    message=f"Invalid workflow status: {state_data.get('status')}",
                    field="status"
                ))
            
            # Check metadata integrity
            metadata = self._load_workflow_metadata(spec_id)
            if metadata and metadata.checksum:
                # Calculate current checksum
                import hashlib
                current_checksum = hashlib.sha256(
                    json.dumps(state_data, sort_keys=True).encode('utf-8')
                ).hexdigest()
                
                if current_checksum != metadata.checksum:
                    warnings.append(ValidationWarning(
                        code="CHECKSUM_MISMATCH",
                        message="Workflow state checksum mismatch detected",
                        suggestion="State may have been modified outside the system"
                    ))
        
        except Exception as e:
            errors.append(ValidationError(
                code="VALIDATION_ERROR",
                message=f"Error validating state integrity: {str(e)}"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _recover_from_backup(self, spec_id: str) -> Tuple[Optional[Any], FileOperationResult]:
        """Attempt recovery from most recent backup."""
        try:
            backups_dir = self.specs_dir / spec_id / self.WORKFLOW_BACKUP_DIR
            if not backups_dir.exists():
                return None, FileOperationResult(
                    success=False,
                    message="No backups available",
                    error_code="NO_BACKUPS"
                )
            
            # Find most recent backup
            backup_files = sorted(backups_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if not backup_files:
                return None, FileOperationResult(
                    success=False,
                    message="No backup files found",
                    error_code="NO_BACKUP_FILES"
                )
            
            # Try to load most recent backup
            for backup_file in backup_files:
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        state_data = json.load(f)
                    
                    workflow_state = self.deserialize_workflow_state(state_data)
                    
                    return workflow_state, FileOperationResult(
                        success=True,
                        message=f"Recovered from backup: {backup_file.name}",
                        path=str(backup_file)
                    )
                    
                except Exception as e:
                    logger.warning(f"Failed to recover from backup {backup_file}: {str(e)}")
                    continue
            
            return None, FileOperationResult(
                success=False,
                message="All backup recovery attempts failed",
                error_code="BACKUP_RECOVERY_FAILED"
            )
            
        except Exception as e:
            return None, FileOperationResult(
                success=False,
                message=f"Backup recovery error: {str(e)}",
                error_code="BACKUP_RECOVERY_ERROR"
            )
    
    def _recover_from_version(self, spec_id: str) -> Tuple[Optional[Any], FileOperationResult]:
        """Attempt recovery from most recent version."""
        try:
            versions = self.list_workflow_versions(spec_id)
            if not versions:
                return None, FileOperationResult(
                    success=False,
                    message="No versions available for recovery",
                    error_code="NO_VERSIONS"
                )
            
            # Try most recent version
            latest_version = versions[0]
            workflow_state = self.deserialize_workflow_state(latest_version.data)
            
            return workflow_state, FileOperationResult(
                success=True,
                message=f"Recovered from version: {latest_version.version_id}",
                path=f"version:{latest_version.version_id}"
            )
            
        except Exception as e:
            return None, FileOperationResult(
                success=False,
                message=f"Version recovery error: {str(e)}",
                error_code="VERSION_RECOVERY_ERROR"
            )
    
    def _recover_from_metadata(self, spec_id: str) -> Tuple[Optional[Any], FileOperationResult]:
        """Attempt recovery by reconstructing from metadata."""
        try:
            # Import here to avoid circular imports
            from .workflow_orchestrator import WorkflowState, ApprovalStatus
            
            metadata = self._load_workflow_metadata(spec_id)
            if not metadata:
                return None, FileOperationResult(
                    success=False,
                    message="No metadata available for recovery",
                    error_code="NO_METADATA"
                )
            
            # Create minimal workflow state from metadata
            workflow_state = WorkflowState(
                spec_id=spec_id,
                current_phase=WorkflowPhase.REQUIREMENTS,  # Reset to beginning
                status=WorkflowStatus.DRAFT,
                approvals={
                    "requirements": ApprovalStatus.PENDING,
                    "design": ApprovalStatus.PENDING,
                    "tasks": ApprovalStatus.PENDING
                },
                metadata={
                    "recovered": True,
                    "recovery_timestamp": datetime.utcnow().isoformat(),
                    "original_version": metadata.version
                }
            )
            
            return workflow_state, FileOperationResult(
                success=True,
                message="Recovered minimal state from metadata",
                path="metadata:recovery"
            )
            
        except Exception as e:
            return None, FileOperationResult(
                success=False,
                message=f"Metadata recovery error: {str(e)}",
                error_code="METADATA_RECOVERY_ERROR"
            )
    
    def _update_workflow_metadata(self, spec_id: str, state_data: Dict[str, Any]) -> FileOperationResult:
        """Update workflow metadata with current state information."""
        try:
            spec_dir = self.specs_dir / spec_id
            metadata_file = spec_dir / self.WORKFLOW_METADATA_FILE
            
            # Calculate checksum
            import hashlib
            checksum = hashlib.sha256(
                json.dumps(state_data, sort_keys=True).encode('utf-8')
            ).hexdigest()
            
            # Load existing metadata or create new
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_data = json.load(f)
                metadata = WorkflowMetadata.from_dict(metadata_data)
                metadata.updated_at = datetime.utcnow()
                metadata.checksum = checksum
            else:
                metadata = WorkflowMetadata(
                    spec_id=spec_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                    checksum=checksum
                )
            
            # Save metadata
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata.to_dict(), f, indent=2, ensure_ascii=False)
            
            return FileOperationResult(
                success=True,
                message="Workflow metadata updated",
                path=str(metadata_file)
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                message=f"Failed to update metadata: {str(e)}",
                error_code="METADATA_UPDATE_ERROR"
            )
    
    def _load_workflow_metadata(self, spec_id: str) -> Optional[WorkflowMetadata]:
        """Load workflow metadata."""
        try:
            metadata_file = self.specs_dir / spec_id / self.WORKFLOW_METADATA_FILE
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_data = json.load(f)
            
            return WorkflowMetadata.from_dict(metadata_data)
            
        except Exception as e:
            logger.warning(f"Failed to load workflow metadata: {str(e)}")
            return None
    
    def _cleanup_old_versions(self, spec_id: str) -> None:
        """Clean up old version files, keeping only the most recent ones."""
        try:
            versions_dir = self.specs_dir / spec_id / self.WORKFLOW_VERSIONS_DIR
            if not versions_dir.exists():
                return
            
            version_files = sorted(
                versions_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            # Remove old versions beyond the limit
            for old_version in version_files[self.MAX_VERSIONS:]:
                try:
                    old_version.unlink()
                    logger.debug(f"Removed old version: {old_version}")
                except Exception as e:
                    logger.warning(f"Failed to remove old version {old_version}: {str(e)}")
        
        except Exception as e:
            logger.warning(f"Error cleaning up old versions: {str(e)}")
    
    def _cleanup_old_backups(self, spec_id: str) -> None:
        """Clean up old backup files, keeping only the most recent ones."""
        try:
            backups_dir = self.specs_dir / spec_id / self.WORKFLOW_BACKUP_DIR
            if not backups_dir.exists():
                return
            
            backup_files = sorted(
                backups_dir.glob("*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            
            # Remove old backups beyond the limit
            for old_backup in backup_files[self.MAX_BACKUPS:]:
                try:
                    old_backup.unlink()
                    logger.debug(f"Removed old backup: {old_backup}")
                except Exception as e:
                    logger.warning(f"Failed to remove old backup {old_backup}: {str(e)}")
        
        except Exception as e:
            logger.warning(f"Error cleaning up old backups: {str(e)}")