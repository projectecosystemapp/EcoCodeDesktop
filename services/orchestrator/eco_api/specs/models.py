"""
Pydantic models for spec-driven workflow management.

This module defines the data models used throughout the spec management system,
including workflow states, document structures, and validation schemas.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import hashlib
import json


class WorkflowPhase(str, Enum):
    """Workflow phases in the spec-driven development process."""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    TASKS = "tasks"
    EXECUTION = "execution"


class WorkflowStatus(str, Enum):
    """Status of a workflow or document."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


class TaskStatus(str, Enum):
    """Status of individual tasks."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class DocumentType(str, Enum):
    """Types of spec documents."""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    TASKS = "tasks"


class ValidationError(BaseModel):
    """Validation error details."""
    code: str
    message: str
    field: Optional[str] = None
    severity: str = "error"


class ValidationWarning(BaseModel):
    """Validation warning details."""
    code: str
    message: str
    field: Optional[str] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of validation operations."""
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationWarning] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    """Metadata for spec documents."""
    created_at: datetime
    updated_at: datetime
    version: str
    checksum: str

    @validator('checksum')
    def validate_checksum(cls, v):
        """Validate checksum format."""
        if not v or len(v) != 64:  # SHA-256 hex length
            raise ValueError("Checksum must be a valid SHA-256 hash")
        return v


class SpecMetadata(BaseModel):
    """Metadata for a complete specification."""
    id: str
    feature_name: str
    version: str
    created_at: datetime
    updated_at: datetime
    current_phase: WorkflowPhase
    status: WorkflowStatus
    checksum: Dict[str, Optional[str]] = Field(default_factory=dict)

    @validator('feature_name')
    def validate_feature_name(cls, v):
        """Validate feature name follows kebab-case format."""
        import re
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', v):
            raise ValueError("Feature name must be in kebab-case format")
        return v


class SpecFileStructure(BaseModel):
    """File structure definition for a spec."""
    spec_id: str
    base_path: str
    files: Dict[str, str]

    @validator('base_path')
    def validate_base_path(cls, v, values):
        """Validate base path format."""
        spec_id = values.get('spec_id')
        if spec_id and not v.endswith(f"/{spec_id}"):
            raise ValueError(f"Base path must end with spec_id: {spec_id}")
        return v


class SpecSummary(BaseModel):
    """Summary information for a spec."""
    id: str
    feature_name: str
    current_phase: WorkflowPhase
    status: WorkflowStatus
    last_updated: datetime
    progress: float = Field(ge=0.0, le=1.0)


class SpecDocument(BaseModel):
    """Generic spec document container."""
    type: DocumentType
    content: str
    metadata: DocumentMetadata

    def calculate_checksum(self) -> str:
        """Calculate SHA-256 checksum of document content."""
        return hashlib.sha256(self.content.encode('utf-8')).hexdigest()

    def validate_checksum(self) -> bool:
        """Validate that stored checksum matches content."""
        return self.metadata.checksum == self.calculate_checksum()

    def update_checksum(self) -> None:
        """Update metadata checksum to match current content."""
        self.metadata.checksum = self.calculate_checksum()
        self.metadata.updated_at = datetime.utcnow()


class CreateSpecRequest(BaseModel):
    """Request to create a new spec."""
    feature_idea: str = Field(..., min_length=3, max_length=500)
    feature_name: Optional[str] = None

    @validator('feature_idea')
    def validate_feature_idea(cls, v):
        """Validate feature idea is not empty or just whitespace."""
        if not v.strip():
            raise ValueError("Feature idea cannot be empty")
        return v.strip()


class UpdateSpecRequest(BaseModel):
    """Request to update an existing spec."""
    phase: WorkflowPhase
    content: Optional[str] = None
    approve: Optional[bool] = None
    feedback: Optional[str] = None


class FileOperationResult(BaseModel):
    """Result of file system operations."""
    success: bool
    message: str
    path: Optional[str] = None
    error_code: Optional[str] = None


class SpecDiscoveryResult(BaseModel):
    """Result of spec discovery operations."""
    specs: List[SpecSummary]
    total_count: int
    errors: List[str] = Field(default_factory=list)