"""
File system manager for spec-driven workflow documents.

This module provides comprehensive file system operations for managing
specification documents, including directory creation, validation,
persistence, and recovery mechanisms.

Requirements addressed:
- 1.1, 1.2: Spec initialization and kebab-case feature name generation
- 7.1, 7.3, 7.4: Standardized directory structure and file organization
- 7.5, 7.6: Document persistence and validation
- 8.6: File integrity and error handling
"""

import os
import json
import hashlib
import shutil
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from uuid import uuid4

from .models import (
    SpecMetadata, SpecFileStructure, SpecDocument, SpecSummary,
    DocumentType, WorkflowPhase, WorkflowStatus, DocumentMetadata,
    ValidationResult, ValidationError, ValidationWarning,
    FileOperationResult, SpecDiscoveryResult
)
from ..security.path_validator import PathValidator, PathValidationError, SecurityLevel


class FileSystemManager:
    """
    Manages file system operations for spec documents.
    
    Provides functionality for creating, validating, and managing
    spec directories and documents with proper error handling and recovery.
    """
    
    SPEC_BASE_PATH = ".kiro/specs"
    METADATA_FILE = ".spec-metadata.json"
    REQUIRED_FILES = ["requirements.md", "design.md", "tasks.md"]
    
    def __init__(self, workspace_root: str = "."):
        """
        Initialize FileSystemManager.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.specs_dir = self.workspace_root / self.SPEC_BASE_PATH
        
        # Initialize path validator for security
        self.path_validator = PathValidator(
            workspace_root=self.workspace_root,
            security_level=SecurityLevel.STRICT,
            allowed_extensions=['.md', '.json'],  # Only allow markdown and JSON files
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
    
    def generate_feature_name(self, rough_idea: str) -> str:
        """
        Generate a kebab-case feature name from a rough idea.
        
        Requirements: 1.1 - Automatic kebab-case feature name generation
        
        Args:
            rough_idea: The rough feature idea text
            
        Returns:
            A kebab-case formatted feature name
        """
        if not rough_idea or not rough_idea.strip():
            raise ValueError("Feature idea cannot be empty")
        
        # Convert to kebab-case
        feature_name = rough_idea.lower().strip()
        
        # Replace spaces and underscores with hyphens
        feature_name = feature_name.replace(" ", "-").replace("_", "-")
        
        # Remove non-alphanumeric characters except hyphens
        feature_name = re.sub(r"[^a-z0-9-]", "", feature_name)
        
        # Clean up consecutive hyphens
        feature_name = re.sub(r"-+", "-", feature_name)
        
        # Remove leading/trailing hyphens
        feature_name = feature_name.strip("-")
        
        # Limit length and ensure minimum length
        if len(feature_name) < 3:
            # If too short, use a more descriptive approach
            words = rough_idea.lower().split()[:3]
            feature_name = "-".join(re.sub(r"[^a-z0-9]", "", word) for word in words if word)
            
        feature_name = feature_name[:50]  # Max 50 characters
        
        # Final validation
        if not feature_name or len(feature_name) < 3:
            # Fallback to UUID-based name
            feature_name = f"feature-{str(uuid4())[:8]}"
            
        return feature_name
    
    def validate_feature_name(self, feature_name: str) -> ValidationResult:
        """
        Validate that a feature name follows kebab-case format and filesystem constraints.
        
        Requirements: 7.2 - Kebab-case formatting and filesystem validation
        
        Args:
            feature_name: The feature name to validate
            
        Returns:
            ValidationResult with any errors or warnings
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        # Check kebab-case format
        kebab_case_regex = r"^[a-z0-9]+(-[a-z0-9]+)*$"
        if not re.match(kebab_case_regex, feature_name):
            errors.append(ValidationError(
                code="INVALID_FEATURE_NAME_FORMAT",
                message="Feature name must be in kebab-case format (lowercase letters, numbers, and hyphens only)",
                field="feature_name"
            ))
        
        # Check length constraints
        if len(feature_name) < 3:
            errors.append(ValidationError(
                code="FEATURE_NAME_TOO_SHORT",
                message="Feature name must be at least 3 characters long",
                field="feature_name"
            ))
        
        if len(feature_name) > 50:
            errors.append(ValidationError(
                code="FEATURE_NAME_TOO_LONG",
                message="Feature name must be 50 characters or less",
                field="feature_name"
            ))
        
        # Check for reserved names (Windows reserved names)
        reserved_names = {
            "con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "com5",
            "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4",
            "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
        }
        if feature_name.lower() in reserved_names:
            errors.append(ValidationError(
                code="RESERVED_FEATURE_NAME",
                message="Feature name cannot be a reserved system name",
                field="feature_name"
            ))
        
        # Check for invalid filesystem characters
        invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
        if re.search(invalid_chars, feature_name):
            errors.append(ValidationError(
                code="INVALID_FILESYSTEM_CHARS",
                message="Feature name contains characters not allowed in filesystem paths",
                field="feature_name"
            ))
        
        # Warnings for best practices
        if feature_name.startswith("-") or feature_name.endswith("-"):
            warnings.append(ValidationWarning(
                code="FEATURE_NAME_HYPHEN_EDGES",
                message="Feature name should not start or end with hyphens",
                field="feature_name",
                suggestion="Remove leading or trailing hyphens"
            ))
        
        if "--" in feature_name:
            warnings.append(ValidationWarning(
                code="CONSECUTIVE_HYPHENS",
                message="Feature name should not contain consecutive hyphens",
                field="feature_name",
                suggestion="Use single hyphens to separate words"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def check_feature_name_uniqueness(self, feature_name: str) -> ValidationResult:
        """
        Check if a feature name is unique within existing specs.
        
        Requirements: 1.2 - Uniqueness checking for feature names
        
        Args:
            feature_name: The feature name to check
            
        Returns:
            ValidationResult indicating if the name is unique
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            existing_specs = self.list_existing_specs()
            existing_names = [spec.feature_name for spec in existing_specs]
            
            if feature_name in existing_names:
                errors.append(ValidationError(
                    code="DUPLICATE_FEATURE_NAME",
                    message=f"A spec with the name '{feature_name}' already exists",
                    field="feature_name"
                ))
            
            # Check for similar names that might cause confusion
            similar_names = [
                name for name in existing_names
                if self._calculate_similarity(feature_name, name) > 0.8 and name != feature_name
            ]
            
            if similar_names:
                warnings.append(ValidationWarning(
                    code="SIMILAR_FEATURE_NAMES",
                    message=f"Similar spec names exist: {', '.join(similar_names)}",
                    field="feature_name",
                    suggestion="Consider using a more distinctive name to avoid confusion"
                ))
                
        except Exception as e:
            # If we can't check uniqueness, it's not a fatal error
            warnings.append(ValidationWarning(
                code="UNIQUENESS_CHECK_FAILED",
                message=f"Could not verify name uniqueness: {str(e)}",
                field="feature_name",
                suggestion="Manually verify the name is unique"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def create_spec_directory(self, feature_name: str) -> FileOperationResult:
        """
        Create a spec directory with proper structure and metadata.
        
        Requirements: 7.1, 7.3 - Standardized directory structure and file organization
        Requirements: 2.1, 2.2 - Path validation and boundary checking
        
        Args:
            feature_name: The kebab-case feature name
            
        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            # Validate feature name first
            validation = self.validate_feature_name(feature_name)
            if not validation.is_valid:
                return FileOperationResult(
                    success=False,
                    message=f"Invalid feature name: {validation.errors[0].message}",
                    error_code="INVALID_FEATURE_NAME"
                )
            
            # Check uniqueness
            uniqueness = self.check_feature_name_uniqueness(feature_name)
            if not uniqueness.is_valid:
                return FileOperationResult(
                    success=False,
                    message=f"Feature name not unique: {uniqueness.errors[0].message}",
                    error_code="DUPLICATE_FEATURE_NAME"
                )
            
            # Validate path security using PathValidator
            spec_dir_path = self.path_validator.secure_join(self.SPEC_BASE_PATH, feature_name)
            path_validation = self._validate_and_secure_path(spec_dir_path, allow_creation=True)
            if not path_validation.success:
                return path_validation
            
            # Create directory structure using validated path
            spec_dir = Path(path_validation.path)
            
            if spec_dir.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Spec directory already exists: {spec_dir}",
                    error_code="DIRECTORY_EXISTS"
                )
            
            # Create the directory
            spec_dir.mkdir(parents=True, exist_ok=False)
            
            # Create initial metadata
            metadata = SpecMetadata(
                id=feature_name,
                feature_name=feature_name,
                version="1.0.0",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                current_phase=WorkflowPhase.REQUIREMENTS,
                status=WorkflowStatus.DRAFT,
                checksum={}
            )
            
            # Save metadata
            metadata_path = spec_dir / self.METADATA_FILE
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.dict(), f, indent=2, default=str)
            
            return FileOperationResult(
                success=True,
                message=f"Successfully created spec directory: {feature_name}",
                path=str(spec_dir)
            )
            
        except PermissionError:
            return FileOperationResult(
                success=False,
                message="Permission denied creating spec directory",
                error_code="PERMISSION_DENIED"
            )
        except OSError as e:
            return FileOperationResult(
                success=False,
                message=f"File system error: {str(e)}",
                error_code="FILESYSTEM_ERROR"
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
                message=f"Unexpected error: {str(e)}",
                error_code="UNKNOWN_ERROR"
            )
    
    def get_spec_file_structure(self, feature_name: str) -> SpecFileStructure:
        """
        Generate the file structure for a spec.
        
        Requirements: 7.1 - Standardized directory structure
        
        Args:
            feature_name: The feature name
            
        Returns:
            SpecFileStructure with all file paths
        """
        base_path = f"{self.SPEC_BASE_PATH}/{feature_name}"
        
        return SpecFileStructure(
            spec_id=feature_name,
            base_path=base_path,
            files={
                "requirements": f"{base_path}/requirements.md",
                "design": f"{base_path}/design.md",
                "tasks": f"{base_path}/tasks.md",
                "metadata": f"{base_path}/{self.METADATA_FILE}"
            }
        )
    
    def validate_spec_structure(self, feature_name: str) -> ValidationResult:
        """
        Validate the structure of an existing spec directory.
        
        Requirements: 7.6 - File structure validation with detailed error reporting
        Requirements: 2.1, 2.2, 2.4 - Path validation and secure file operations
        
        Args:
            feature_name: The feature name to validate
            
        Returns:
            ValidationResult with detailed validation information
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            # Validate and secure the feature name path
            spec_dir_path = self.path_validator.secure_join(self.SPEC_BASE_PATH, feature_name)
            path_validation = self._validate_and_secure_path(spec_dir_path, allow_creation=False)
            if not path_validation.success:
                errors.append(ValidationError(
                    code="PATH_VALIDATION_ERROR",
                    message=f"Path validation failed: {path_validation.message}",
                    field="feature_name"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            spec_dir = Path(path_validation.path)
            
            # Check if directory exists
            if not spec_dir.exists():
                errors.append(ValidationError(
                    code="SPEC_DIRECTORY_NOT_FOUND",
                    message=f"Spec directory does not exist: {spec_dir}",
                    field="spec_directory"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            if not spec_dir.is_dir():
                errors.append(ValidationError(
                    code="SPEC_PATH_NOT_DIRECTORY",
                    message=f"Spec path exists but is not a directory: {spec_dir}",
                    field="spec_directory"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Check metadata file
            metadata_path = spec_dir / self.METADATA_FILE
            if not metadata_path.exists():
                errors.append(ValidationError(
                    code="METADATA_FILE_MISSING",
                    message=f"Metadata file missing: {metadata_path}",
                    field="metadata_file"
                ))
            else:
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata_data = json.load(f)
                    SpecMetadata(**metadata_data)  # Validate structure
                except (json.JSONDecodeError, ValueError) as e:
                    errors.append(ValidationError(
                        code="INVALID_METADATA_FORMAT",
                        message=f"Invalid metadata format: {str(e)}",
                        field="metadata_file"
                    ))
            
            # Check for required files (optional at this stage)
            for file_name in self.REQUIRED_FILES:
                file_path = spec_dir / file_name
                if not file_path.exists():
                    warnings.append(ValidationWarning(
                        code="SPEC_FILE_MISSING",
                        message=f"Spec file missing: {file_name}",
                        field=file_name.replace('.md', ''),
                        suggestion=f"Create {file_name} to complete the spec"
                    ))
                elif file_path.stat().st_size == 0:
                    warnings.append(ValidationWarning(
                        code="SPEC_FILE_EMPTY",
                        message=f"Spec file is empty: {file_name}",
                        field=file_name.replace('.md', ''),
                        suggestion=f"Add content to {file_name}"
                    ))
            
            # Check for unexpected files
            expected_files = set(self.REQUIRED_FILES + [self.METADATA_FILE])
            actual_files = {f.name for f in spec_dir.iterdir() if f.is_file()}
            unexpected_files = actual_files - expected_files
            
            if unexpected_files:
                warnings.append(ValidationWarning(
                    code="UNEXPECTED_FILES",
                    message=f"Unexpected files in spec directory: {', '.join(unexpected_files)}",
                    field="spec_directory",
                    suggestion="Remove or relocate unexpected files"
                ))
            
        except Exception as e:
            errors.append(ValidationError(
                code="VALIDATION_ERROR",
                message=f"Error validating spec structure: {str(e)}",
                field="spec_directory"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def list_existing_specs(self) -> List[SpecSummary]:
        """
        List all existing specs in the workspace.
        
        Requirements: 7.9 - Spec discovery and listing functionality
        
        Returns:
            List of SpecSummary objects for existing specs
        """
        specs: List[SpecSummary] = []
        
        try:
            if not self.specs_dir.exists():
                return specs
            
            for spec_dir in self.specs_dir.iterdir():
                if not spec_dir.is_dir():
                    continue
                
                try:
                    metadata_path = spec_dir / self.METADATA_FILE
                    if not metadata_path.exists():
                        continue
                    
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata_data = json.load(f)
                    
                    metadata = SpecMetadata(**metadata_data)
                    
                    # Calculate progress based on existing files
                    progress = self._calculate_spec_progress(spec_dir)
                    
                    specs.append(SpecSummary(
                        id=metadata.id,
                        feature_name=metadata.feature_name,
                        current_phase=metadata.current_phase,
                        status=metadata.status,
                        last_updated=metadata.updated_at,
                        progress=progress
                    ))
                    
                except Exception:
                    # Skip invalid specs
                    continue
        
        except Exception:
            # Return empty list if there's an error accessing the directory
            pass
        
        return sorted(specs, key=lambda x: x.last_updated, reverse=True)
    
    def _calculate_spec_progress(self, spec_dir: Path) -> float:
        """
        Calculate progress of a spec based on existing files.
        
        Args:
            spec_dir: Path to the spec directory
            
        Returns:
            Progress as a float between 0.0 and 1.0
        """
        total_files = len(self.REQUIRED_FILES)
        existing_files = 0
        
        for file_name in self.REQUIRED_FILES:
            file_path = spec_dir / file_name
            if file_path.exists() and file_path.stat().st_size > 0:
                existing_files += 1
        
        return existing_files / total_files if total_files > 0 else 0.0
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using Levenshtein distance.
        
        Args:
            str1: First string
            str2: Second string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if str1 == str2:
            return 1.0
        
        len1, len2 = len(str1), len(str2)
        if len1 == 0 or len2 == 0:
            return 0.0
        
        # Create matrix for dynamic programming
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # Initialize first row and column
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j
        
        # Fill the matrix
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if str1[i-1] == str2[j-1] else 1
                matrix[i][j] = min(
                    matrix[i-1][j] + 1,      # deletion
                    matrix[i][j-1] + 1,      # insertion
                    matrix[i-1][j-1] + cost  # substitution
                )
        
        # Calculate similarity
        max_len = max(len1, len2)
        distance = matrix[len1][len2]
        return (max_len - distance) / max_len
    
    def save_document(self, feature_name: str, document_type: DocumentType, content: str) -> FileOperationResult:
        """
        Save a document to the spec directory with checksum validation.
        
        Requirements: 7.5 - Document persistence with proper error handling
        Requirements: 2.1, 2.2, 2.4 - Path validation and secure file operations
        
        Args:
            feature_name: The feature name
            document_type: Type of document to save
            content: Document content
            
        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            # Validate and secure the feature name path
            spec_dir_path = self.path_validator.secure_join(self.SPEC_BASE_PATH, feature_name)
            spec_dir_validation = self._validate_and_secure_path(spec_dir_path, allow_creation=False)
            if not spec_dir_validation.success:
                return spec_dir_validation
            
            spec_dir = Path(spec_dir_validation.path)
            
            # Validate spec directory exists
            if not spec_dir.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Spec directory does not exist: {feature_name}",
                    error_code="SPEC_NOT_FOUND"
                )
            
            # Validate and secure the file path
            file_name = f"{document_type.value}.md"
            file_path_str = self.path_validator.secure_join(self.SPEC_BASE_PATH, feature_name, file_name)
            file_path_validation = self._validate_and_secure_path(file_path_str, allow_creation=True)
            if not file_path_validation.success:
                return file_path_validation
            
            file_path = Path(file_path_validation.path)
            
            # Create document metadata
            now = datetime.utcnow()
            checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Create backup if file exists
            if file_path.exists():
                backup_path = file_path.with_suffix(f".md.backup.{int(now.timestamp())}")
                shutil.copy2(file_path, backup_path)
            
            # Write document content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update metadata
            metadata_result = self._update_spec_metadata(feature_name, document_type, checksum)
            if not metadata_result.success:
                # Rollback file write if metadata update fails
                if file_path.exists():
                    file_path.unlink()
                return metadata_result
            
            return FileOperationResult(
                success=True,
                message=f"Successfully saved {document_type.value} document",
                path=str(file_path)
            )
            
        except PermissionError:
            return FileOperationResult(
                success=False,
                message="Permission denied writing document",
                error_code="PERMISSION_DENIED"
            )
        except OSError as e:
            return FileOperationResult(
                success=False,
                message=f"File system error: {str(e)}",
                error_code="FILESYSTEM_ERROR"
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
                message=f"Unexpected error saving document: {str(e)}",
                error_code="UNKNOWN_ERROR"
            )
    
    def load_document(self, feature_name: str, document_type: DocumentType) -> Tuple[Optional[SpecDocument], FileOperationResult]:
        """
        Load a document from the spec directory with integrity checking.
        
        Requirements: 7.5, 7.6 - Document loading with checksum validation
        Requirements: 2.1, 2.2, 2.4 - Path validation and secure file operations
        
        Args:
            feature_name: The feature name
            document_type: Type of document to load
            
        Returns:
            Tuple of (SpecDocument or None, FileOperationResult)
        """
        try:
            # Validate and secure the feature name path
            spec_dir_path = self.path_validator.secure_join(self.SPEC_BASE_PATH, feature_name)
            spec_dir_validation = self._validate_and_secure_path(spec_dir_path, allow_creation=False)
            if not spec_dir_validation.success:
                return None, spec_dir_validation
            
            spec_dir = Path(spec_dir_validation.path)
            
            # Validate spec directory exists
            if not spec_dir.exists():
                return None, FileOperationResult(
                    success=False,
                    message=f"Spec directory does not exist: {feature_name}",
                    error_code="SPEC_NOT_FOUND"
                )
            
            # Validate and secure the file path
            file_name = f"{document_type.value}.md"
            file_path_str = self.path_validator.secure_join(self.SPEC_BASE_PATH, feature_name, file_name)
            file_path_validation = self._validate_and_secure_path(file_path_str, allow_creation=False)
            if not file_path_validation.success:
                return None, file_path_validation
            
            file_path = Path(file_path_validation.path)
            
            if not file_path.exists():
                return None, FileOperationResult(
                    success=False,
                    message=f"Document file does not exist: {file_name}",
                    error_code="DOCUMENT_NOT_FOUND"
                )
            
            # Read document content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Load metadata to get stored checksum
            metadata = self._load_spec_metadata(feature_name)
            if not metadata:
                return None, FileOperationResult(
                    success=False,
                    message="Could not load spec metadata",
                    error_code="METADATA_ERROR"
                )
            
            # Calculate current checksum
            current_checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
            stored_checksum = metadata.checksum.get(document_type.value)
            
            # Create document metadata
            file_stat = file_path.stat()
            doc_metadata = DocumentMetadata(
                created_at=datetime.fromtimestamp(file_stat.st_ctime),
                updated_at=datetime.fromtimestamp(file_stat.st_mtime),
                version=metadata.version,
                checksum=current_checksum
            )
            
            # Create document
            document = SpecDocument(
                type=document_type,
                content=content,
                metadata=doc_metadata
            )
            
            # Check integrity
            integrity_valid = stored_checksum is None or stored_checksum == current_checksum
            
            result = FileOperationResult(
                success=True,
                message=f"Successfully loaded {document_type.value} document",
                path=str(file_path)
            )
            
            if not integrity_valid:
                result.message += " (WARNING: Checksum mismatch detected)"
                result.error_code = "CHECKSUM_MISMATCH"
            
            return document, result
            
        except PermissionError:
            return None, FileOperationResult(
                success=False,
                message="Permission denied reading document",
                error_code="PERMISSION_DENIED"
            )
        except OSError as e:
            return None, FileOperationResult(
                success=False,
                message=f"File system error: {str(e)}",
                error_code="FILESYSTEM_ERROR"
            )
        except PathValidationError as e:
            return None, FileOperationResult(
                success=False,
                message=f"Path security error: {str(e)}",
                error_code="PATH_SECURITY_ERROR"
            )
        except Exception as e:
            return None, FileOperationResult(
                success=False,
                message=f"Unexpected error loading document: {str(e)}",
                error_code="UNKNOWN_ERROR"
            )
    
    def validate_document_integrity(self, feature_name: str, document_type: DocumentType) -> ValidationResult:
        """
        Validate document integrity using checksum comparison.
        
        Requirements: 7.6, 8.6 - Document checksum validation for integrity checking
        
        Args:
            feature_name: The feature name
            document_type: Type of document to validate
            
        Returns:
            ValidationResult with integrity status
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            document, load_result = self.load_document(feature_name, document_type)
            
            if not load_result.success:
                errors.append(ValidationError(
                    code="DOCUMENT_LOAD_FAILED",
                    message=load_result.message,
                    field=document_type.value
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            if load_result.error_code == "CHECKSUM_MISMATCH":
                errors.append(ValidationError(
                    code="CHECKSUM_MISMATCH",
                    message=f"Document {document_type.value} has been modified outside the system",
                    field=document_type.value
                ))
            
            # Additional content validation
            if document and len(document.content.strip()) == 0:
                warnings.append(ValidationWarning(
                    code="EMPTY_DOCUMENT",
                    message=f"Document {document_type.value} is empty",
                    field=document_type.value,
                    suggestion="Add content to the document"
                ))
            
        except Exception as e:
            errors.append(ValidationError(
                code="VALIDATION_ERROR",
                message=f"Error validating document integrity: {str(e)}",
                field=document_type.value
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def discover_specs(self, include_invalid: bool = False) -> SpecDiscoveryResult:
        """
        Discover and list all specs with detailed information.
        
        Requirements: 7.11 - Spec discovery and listing functionality
        
        Args:
            include_invalid: Whether to include specs with validation errors
            
        Returns:
            SpecDiscoveryResult with discovered specs and any errors
        """
        specs: List[SpecSummary] = []
        errors: List[str] = []
        
        try:
            if not self.specs_dir.exists():
                return SpecDiscoveryResult(specs=specs, total_count=0, errors=errors)
            
            for spec_dir in self.specs_dir.iterdir():
                if not spec_dir.is_dir():
                    continue
                
                feature_name = spec_dir.name
                
                try:
                    # Validate spec structure
                    validation = self.validate_spec_structure(feature_name)
                    
                    if not validation.is_valid and not include_invalid:
                        errors.append(f"Invalid spec '{feature_name}': {validation.errors[0].message}")
                        continue
                    
                    # Load metadata
                    metadata = self._load_spec_metadata(feature_name)
                    if not metadata:
                        if include_invalid:
                            # Create minimal summary for invalid spec
                            specs.append(SpecSummary(
                                id=feature_name,
                                feature_name=feature_name,
                                current_phase=WorkflowPhase.REQUIREMENTS,
                                status=WorkflowStatus.ERROR,
                                last_updated=datetime.fromtimestamp(spec_dir.stat().st_mtime),
                                progress=0.0
                            ))
                        else:
                            errors.append(f"Could not load metadata for spec '{feature_name}'")
                        continue
                    
                    # Calculate progress
                    progress = self._calculate_spec_progress(spec_dir)
                    
                    # Validate document integrity
                    integrity_issues = []
                    for doc_type in DocumentType:
                        integrity = self.validate_document_integrity(feature_name, doc_type)
                        if not integrity.is_valid:
                            integrity_issues.extend([error.message for error in integrity.errors])
                    
                    # Adjust status based on integrity
                    status = metadata.status
                    if integrity_issues and status != WorkflowStatus.ERROR:
                        status = WorkflowStatus.ERROR
                        errors.extend(integrity_issues)
                    
                    specs.append(SpecSummary(
                        id=metadata.id,
                        feature_name=metadata.feature_name,
                        current_phase=metadata.current_phase,
                        status=status,
                        last_updated=metadata.updated_at,
                        progress=progress
                    ))
                    
                except Exception as e:
                    error_msg = f"Error processing spec '{feature_name}': {str(e)}"
                    errors.append(error_msg)
                    
                    if include_invalid:
                        # Create error summary
                        specs.append(SpecSummary(
                            id=feature_name,
                            feature_name=feature_name,
                            current_phase=WorkflowPhase.REQUIREMENTS,
                            status=WorkflowStatus.ERROR,
                            last_updated=datetime.fromtimestamp(spec_dir.stat().st_mtime),
                            progress=0.0
                        ))
        
        except Exception as e:
            errors.append(f"Error discovering specs: {str(e)}")
        
        # Sort by last updated (most recent first)
        specs.sort(key=lambda x: x.last_updated, reverse=True)
        
        return SpecDiscoveryResult(
            specs=specs,
            total_count=len(specs),
            errors=errors
        )
    
    def _update_spec_metadata(self, feature_name: str, document_type: DocumentType, checksum: str) -> FileOperationResult:
        """
        Update spec metadata with new document checksum.
        
        Args:
            feature_name: The feature name
            document_type: Type of document updated
            checksum: New checksum for the document
            
        Returns:
            FileOperationResult indicating success or failure
        """
        try:
            spec_dir = self.specs_dir / feature_name
            metadata_path = spec_dir / self.METADATA_FILE
            
            # Load existing metadata
            metadata = self._load_spec_metadata(feature_name)
            if not metadata:
                return FileOperationResult(
                    success=False,
                    message="Could not load existing metadata",
                    error_code="METADATA_ERROR"
                )
            
            # Update checksum and timestamp
            metadata.checksum[document_type.value] = checksum
            metadata.updated_at = datetime.utcnow()
            
            # Save updated metadata
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata.dict(), f, indent=2, default=str)
            
            return FileOperationResult(
                success=True,
                message="Metadata updated successfully"
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                message=f"Error updating metadata: {str(e)}",
                error_code="METADATA_UPDATE_ERROR"
            )
    
    def _load_spec_metadata(self, feature_name: str) -> Optional[SpecMetadata]:
        """
        Load spec metadata from file.
        
        Args:
            feature_name: The feature name
            
        Returns:
            SpecMetadata object or None if loading fails
        """
        try:
            spec_dir = self.specs_dir / feature_name
            metadata_path = spec_dir / self.METADATA_FILE
            
            if not metadata_path.exists():
                return None
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_data = json.load(f)
            
            return SpecMetadata(**metadata_data)
            
        except Exception:
            return None
    
    def detect_file_corruption(self, feature_name: str) -> ValidationResult:
        """
        Detect file corruption in a spec directory.
        
        Requirements: 7.10, 8.6 - File corruption detection and recovery procedures
        
        Args:
            feature_name: The feature name to check
            
        Returns:
            ValidationResult with corruption detection results
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            spec_dir = self.specs_dir / feature_name
            
            if not spec_dir.exists():
                errors.append(ValidationError(
                    code="SPEC_DIRECTORY_MISSING",
                    message=f"Spec directory does not exist: {feature_name}",
                    field="spec_directory"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Check metadata file corruption
            metadata_path = spec_dir / self.METADATA_FILE
            if metadata_path.exists():
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata_data = json.load(f)
                    SpecMetadata(**metadata_data)  # Validate structure
                except (json.JSONDecodeError, ValueError) as e:
                    errors.append(ValidationError(
                        code="METADATA_CORRUPTED",
                        message=f"Metadata file is corrupted: {str(e)}",
                        field="metadata"
                    ))
            else:
                errors.append(ValidationError(
                    code="METADATA_MISSING",
                    message="Metadata file is missing",
                    field="metadata"
                ))
            
            # Check document file corruption
            for doc_type in DocumentType:
                file_name = f"{doc_type.value}.md"
                file_path = spec_dir / file_name
                
                if file_path.exists():
                    try:
                        # Check if file is readable
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Check for binary content in text file
                        try:
                            content.encode('utf-8')
                        except UnicodeEncodeError:
                            errors.append(ValidationError(
                                code="DOCUMENT_ENCODING_ERROR",
                                message=f"Document {file_name} has encoding issues",
                                field=doc_type.value
                            ))
                        
                        # Check for extremely large files (potential corruption)
                        if len(content) > 10 * 1024 * 1024:  # 10MB
                            warnings.append(ValidationWarning(
                                code="DOCUMENT_UNUSUALLY_LARGE",
                                message=f"Document {file_name} is unusually large ({len(content)} bytes)",
                                field=doc_type.value,
                                suggestion="Verify document content is correct"
                            ))
                        
                        # Validate checksum if available
                        integrity_result = self.validate_document_integrity(feature_name, doc_type)
                        if not integrity_result.is_valid:
                            errors.extend(integrity_result.errors)
                        
                    except (OSError, PermissionError) as e:
                        errors.append(ValidationError(
                            code="DOCUMENT_READ_ERROR",
                            message=f"Cannot read document {file_name}: {str(e)}",
                            field=doc_type.value
                        ))
            
            # Check for orphaned backup files
            backup_files = list(spec_dir.glob("*.backup.*"))
            if backup_files:
                warnings.append(ValidationWarning(
                    code="BACKUP_FILES_PRESENT",
                    message=f"Found {len(backup_files)} backup files",
                    field="spec_directory",
                    suggestion="Clean up old backup files if no longer needed"
                ))
            
        except Exception as e:
            errors.append(ValidationError(
                code="CORRUPTION_CHECK_ERROR",
                message=f"Error checking for corruption: {str(e)}",
                field="spec_directory"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def recover_spec_structure(self, feature_name: str, create_missing: bool = True) -> FileOperationResult:
        """
        Attempt to recover a corrupted spec structure.
        
        Requirements: 7.10, 8.10 - File corruption detection and recovery procedures
        
        Args:
            feature_name: The feature name to recover
            create_missing: Whether to create missing files with templates
            
        Returns:
            FileOperationResult indicating recovery success
        """
        try:
            spec_dir = self.specs_dir / feature_name
            recovery_actions = []
            
            # Ensure directory exists
            if not spec_dir.exists():
                if create_missing:
                    spec_dir.mkdir(parents=True, exist_ok=True)
                    recovery_actions.append("Created missing spec directory")
                else:
                    return FileOperationResult(
                        success=False,
                        message="Spec directory does not exist and create_missing=False",
                        error_code="DIRECTORY_MISSING"
                    )
            
            # Recover metadata file
            metadata_path = spec_dir / self.METADATA_FILE
            if not metadata_path.exists() or not self._is_valid_metadata(metadata_path):
                if create_missing:
                    # Create new metadata
                    metadata = SpecMetadata(
                        id=feature_name,
                        feature_name=feature_name,
                        version="1.0.0",
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        current_phase=WorkflowPhase.REQUIREMENTS,
                        status=WorkflowStatus.DRAFT,
                        checksum={}
                    )
                    
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata.dict(), f, indent=2, default=str)
                    
                    recovery_actions.append("Recreated metadata file")
            
            # Recover document files
            for doc_type in DocumentType:
                file_name = f"{doc_type.value}.md"
                file_path = spec_dir / file_name
                
                if not file_path.exists() and create_missing:
                    # Create template content
                    template_content = self._get_document_template(doc_type)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(template_content)
                    
                    recovery_actions.append(f"Created template {file_name}")
                
                elif file_path.exists():
                    # Check if file is corrupted and try to recover
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # If file is empty, add template
                        if not content.strip() and create_missing:
                            template_content = self._get_document_template(doc_type)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(template_content)
                            recovery_actions.append(f"Added template content to empty {file_name}")
                        
                    except (OSError, UnicodeDecodeError):
                        # File is corrupted, try to recover from backup
                        backup_recovered = self._recover_from_backup(file_path)
                        if backup_recovered:
                            recovery_actions.append(f"Recovered {file_name} from backup")
                        elif create_missing:
                            # Create new template
                            template_content = self._get_document_template(doc_type)
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(template_content)
                            recovery_actions.append(f"Replaced corrupted {file_name} with template")
            
            # Update metadata checksums
            metadata = self._load_spec_metadata(feature_name)
            if metadata:
                for doc_type in DocumentType:
                    file_path = spec_dir / f"{doc_type.value}.md"
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
                        metadata.checksum[doc_type.value] = checksum
                
                metadata.updated_at = datetime.utcnow()
                
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata.dict(), f, indent=2, default=str)
                
                recovery_actions.append("Updated metadata checksums")
            
            message = f"Recovery completed. Actions taken: {'; '.join(recovery_actions)}" if recovery_actions else "No recovery actions needed"
            
            return FileOperationResult(
                success=True,
                message=message,
                path=str(spec_dir)
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                message=f"Recovery failed: {str(e)}",
                error_code="RECOVERY_ERROR"
            )
    
    def cleanup_spec_directory(self, feature_name: str, remove_backups: bool = False) -> FileOperationResult:
        """
        Clean up a spec directory by removing temporary and backup files.
        
        Requirements: 8.10 - System resilience and data protection
        
        Args:
            feature_name: The feature name to clean up
            remove_backups: Whether to remove backup files
            
        Returns:
            FileOperationResult indicating cleanup success
        """
        try:
            spec_dir = self.specs_dir / feature_name
            
            if not spec_dir.exists():
                return FileOperationResult(
                    success=False,
                    message=f"Spec directory does not exist: {feature_name}",
                    error_code="SPEC_NOT_FOUND"
                )
            
            cleanup_actions = []
            
            # Remove temporary files
            temp_patterns = ["*.tmp", "*.temp", "*~", ".DS_Store", "Thumbs.db"]
            for pattern in temp_patterns:
                temp_files = list(spec_dir.glob(pattern))
                for temp_file in temp_files:
                    temp_file.unlink()
                    cleanup_actions.append(f"Removed temporary file: {temp_file.name}")
            
            # Remove backup files if requested
            if remove_backups:
                backup_files = list(spec_dir.glob("*.backup.*"))
                for backup_file in backup_files:
                    backup_file.unlink()
                    cleanup_actions.append(f"Removed backup file: {backup_file.name}")
            
            # Remove empty subdirectories
            for item in spec_dir.iterdir():
                if item.is_dir() and not any(item.iterdir()):
                    item.rmdir()
                    cleanup_actions.append(f"Removed empty directory: {item.name}")
            
            message = f"Cleanup completed. Actions taken: {'; '.join(cleanup_actions)}" if cleanup_actions else "No cleanup actions needed"
            
            return FileOperationResult(
                success=True,
                message=message,
                path=str(spec_dir)
            )
            
        except Exception as e:
            return FileOperationResult(
                success=False,
                message=f"Cleanup failed: {str(e)}",
                error_code="CLEANUP_ERROR"
            )
    
    def _is_valid_metadata(self, metadata_path: Path) -> bool:
        """
        Check if a metadata file is valid.
        
        Args:
            metadata_path: Path to the metadata file
            
        Returns:
            True if metadata is valid, False otherwise
        """
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata_data = json.load(f)
            SpecMetadata(**metadata_data)
            return True
        except Exception:
            return False
    
    def _recover_from_backup(self, file_path: Path) -> bool:
        """
        Attempt to recover a file from its most recent backup.
        
        Args:
            file_path: Path to the file to recover
            
        Returns:
            True if recovery was successful, False otherwise
        """
        try:
            backup_pattern = f"{file_path.name}.backup.*"
            backup_files = list(file_path.parent.glob(backup_pattern))
            
            if not backup_files:
                return False
            
            # Find the most recent backup
            most_recent_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
            
            # Copy backup to original location
            shutil.copy2(most_recent_backup, file_path)
            return True
            
        except Exception:
            return False
    
    def _get_document_template(self, document_type: DocumentType) -> str:
        """
        Get template content for a document type.
        
        Args:
            document_type: Type of document
            
        Returns:
            Template content string
        """
        templates = {
            DocumentType.REQUIREMENTS: """# Requirements Document

## Introduction

[Provide an introduction to the feature and its purpose]

## Requirements

### Requirement 1: [Requirement Title]

**User Story:** As a [role], I want [feature], so that [benefit]

#### Acceptance Criteria

1. WHEN [condition] THEN [system] SHALL [response]
2. IF [precondition] THEN [system] SHALL [response]

""",
            DocumentType.DESIGN: """# Design Document

## Overview

[Provide a high-level overview of the feature design]

## Architecture

[Describe the system architecture and components]

## Components and Interfaces

[Detail the components and their interfaces]

## Data Models

[Define the data models and schemas]

## Error Handling

[Describe error handling strategies]

## Testing Strategy

[Outline the testing approach]

""",
            DocumentType.TASKS: """# Implementation Plan

- [ ] 1. [First task description]
  - [Task details and requirements]
  - _Requirements: [requirement references]_

- [ ] 2. [Second task description]
  - [Task details and requirements]
  - _Requirements: [requirement references]_

"""
        }
        
        return templates.get(document_type, "# Document\n\n[Add content here]\n")