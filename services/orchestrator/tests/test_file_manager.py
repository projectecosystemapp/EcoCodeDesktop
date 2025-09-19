"""
Unit tests for the FileSystemManager class.

Tests all file system operations including directory creation, document persistence,
validation, and recovery mechanisms.
"""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from eco_api.specs.file_manager import FileSystemManager
from eco_api.specs.models import (
    DocumentType, WorkflowPhase, WorkflowStatus, SpecMetadata,
    ValidationResult, FileOperationResult
)


class TestFileSystemManager:
    """Test suite for FileSystemManager."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def file_manager(self, temp_workspace):
        """Create a FileSystemManager instance with temporary workspace."""
        return FileSystemManager(workspace_root=temp_workspace)
    
    def test_generate_feature_name_basic(self, file_manager):
        """Test basic feature name generation."""
        result = file_manager.generate_feature_name("User Authentication System")
        assert result == "user-authentication-system"
    
    def test_generate_feature_name_special_chars(self, file_manager):
        """Test feature name generation with special characters."""
        result = file_manager.generate_feature_name("API & Database Integration!")
        assert result == "api-database-integration"
    
    def test_generate_feature_name_empty_input(self, file_manager):
        """Test feature name generation with empty input."""
        with pytest.raises(ValueError, match="Feature idea cannot be empty"):
            file_manager.generate_feature_name("")
    
    def test_generate_feature_name_short_input(self, file_manager):
        """Test feature name generation with very short input."""
        result = file_manager.generate_feature_name("AI")
        # Should fallback to UUID-based name
        assert result.startswith("feature-")
        assert len(result) > 10
    
    def test_validate_feature_name_valid(self, file_manager):
        """Test validation of valid feature names."""
        valid_names = [
            "user-auth",
            "api-integration",
            "data-processing-engine",
            "feature-123"
        ]
        
        for name in valid_names:
            result = file_manager.validate_feature_name(name)
            assert result.is_valid, f"Name '{name}' should be valid"
            assert len(result.errors) == 0
    
    def test_validate_feature_name_invalid_format(self, file_manager):
        """Test validation of invalid feature name formats."""
        invalid_names = [
            "UserAuth",  # CamelCase
            "user_auth",  # underscore
            "user auth",  # space
            "user-",      # trailing hyphen
            "-user",      # leading hyphen
            "user--auth", # consecutive hyphens
            "ab",         # too short
            "a" * 51      # too long
        ]
        
        for name in invalid_names:
            result = file_manager.validate_feature_name(name)
            assert not result.is_valid, f"Name '{name}' should be invalid"
            assert len(result.errors) > 0
    
    def test_validate_feature_name_reserved(self, file_manager):
        """Test validation of reserved system names."""
        reserved_names = ["con", "prn", "aux", "nul", "com1", "lpt1"]
        
        for name in reserved_names:
            result = file_manager.validate_feature_name(name)
            assert not result.is_valid
            assert any(error.code == "RESERVED_FEATURE_NAME" for error in result.errors)
    
    def test_check_feature_name_uniqueness_new(self, file_manager):
        """Test uniqueness check for new feature name."""
        result = file_manager.check_feature_name_uniqueness("new-feature")
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_check_feature_name_uniqueness_duplicate(self, file_manager, temp_workspace):
        """Test uniqueness check for duplicate feature name."""
        # Create an existing spec
        existing_spec_dir = Path(temp_workspace) / ".kiro/specs/existing-feature"
        existing_spec_dir.mkdir(parents=True)
        
        metadata = SpecMetadata(
            id="existing-feature",
            feature_name="existing-feature",
            version="1.0.0",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            current_phase=WorkflowPhase.REQUIREMENTS,
            status=WorkflowStatus.DRAFT,
            checksum={}
        )
        
        metadata_path = existing_spec_dir / ".spec-metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata.dict(), f, default=str)
        
        result = file_manager.check_feature_name_uniqueness("existing-feature")
        assert not result.is_valid
        assert any(error.code == "DUPLICATE_FEATURE_NAME" for error in result.errors)
    
    def test_create_spec_directory_success(self, file_manager, temp_workspace):
        """Test successful spec directory creation."""
        result = file_manager.create_spec_directory("test-feature")
        
        assert result.success
        assert "Successfully created spec directory" in result.message
        
        # Verify directory structure
        spec_dir = Path(temp_workspace) / ".kiro/specs/test-feature"
        assert spec_dir.exists()
        assert spec_dir.is_dir()
        
        # Verify metadata file
        metadata_path = spec_dir / ".spec-metadata.json"
        assert metadata_path.exists()
        
        with open(metadata_path, 'r') as f:
            metadata_data = json.load(f)
        
        metadata = SpecMetadata(**metadata_data)
        assert metadata.feature_name == "test-feature"
        assert metadata.current_phase == WorkflowPhase.REQUIREMENTS
        assert metadata.status == WorkflowStatus.DRAFT
    
    def test_create_spec_directory_invalid_name(self, file_manager):
        """Test spec directory creation with invalid name."""
        result = file_manager.create_spec_directory("Invalid Name")
        
        assert not result.success
        assert result.error_code == "INVALID_FEATURE_NAME"
    
    def test_create_spec_directory_duplicate(self, file_manager, temp_workspace):
        """Test spec directory creation with duplicate name."""
        # Create first spec
        file_manager.create_spec_directory("test-feature")
        
        # Try to create duplicate
        result = file_manager.create_spec_directory("test-feature")
        
        assert not result.success
        assert result.error_code == "DUPLICATE_FEATURE_NAME"
    
    def test_save_document_success(self, file_manager, temp_workspace):
        """Test successful document saving."""
        # Create spec directory first
        file_manager.create_spec_directory("test-feature")
        
        content = "# Test Requirements\n\nThis is a test document."
        result = file_manager.save_document("test-feature", DocumentType.REQUIREMENTS, content)
        
        assert result.success
        assert "Successfully saved requirements document" in result.message
        
        # Verify file exists and content is correct
        spec_dir = Path(temp_workspace) / ".kiro/specs/test-feature"
        req_file = spec_dir / "requirements.md"
        assert req_file.exists()
        
        with open(req_file, 'r') as f:
            saved_content = f.read()
        assert saved_content == content
    
    def test_save_document_spec_not_found(self, file_manager):
        """Test document saving when spec doesn't exist."""
        content = "# Test Requirements"
        result = file_manager.save_document("nonexistent-spec", DocumentType.REQUIREMENTS, content)
        
        assert not result.success
        assert result.error_code == "SPEC_NOT_FOUND"
    
    def test_load_document_success(self, file_manager, temp_workspace):
        """Test successful document loading."""
        # Create spec and save document
        file_manager.create_spec_directory("test-feature")
        content = "# Test Requirements\n\nThis is a test document."
        file_manager.save_document("test-feature", DocumentType.REQUIREMENTS, content)
        
        # Load document
        document, result = file_manager.load_document("test-feature", DocumentType.REQUIREMENTS)
        
        assert result.success
        assert document is not None
        assert document.type == DocumentType.REQUIREMENTS
        assert document.content == content
        assert document.metadata.checksum is not None
    
    def test_load_document_not_found(self, file_manager):
        """Test loading document when spec doesn't exist."""
        document, result = file_manager.load_document("nonexistent-spec", DocumentType.REQUIREMENTS)
        
        assert not result.success
        assert document is None
        assert result.error_code == "SPEC_NOT_FOUND"
    
    def test_load_document_file_not_found(self, file_manager, temp_workspace):
        """Test loading document when file doesn't exist."""
        # Create spec directory but no document
        file_manager.create_spec_directory("test-feature")
        
        document, result = file_manager.load_document("test-feature", DocumentType.REQUIREMENTS)
        
        assert not result.success
        assert document is None
        assert result.error_code == "DOCUMENT_NOT_FOUND"
    
    def test_validate_document_integrity_success(self, file_manager, temp_workspace):
        """Test document integrity validation with valid document."""
        # Create spec and save document
        file_manager.create_spec_directory("test-feature")
        content = "# Test Requirements"
        file_manager.save_document("test-feature", DocumentType.REQUIREMENTS, content)
        
        result = file_manager.validate_document_integrity("test-feature", DocumentType.REQUIREMENTS)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_spec_structure_valid(self, file_manager, temp_workspace):
        """Test spec structure validation with valid structure."""
        # Create spec directory
        file_manager.create_spec_directory("test-feature")
        
        result = file_manager.validate_spec_structure("test-feature")
        
        assert result.is_valid
        assert len(result.errors) == 0
        # Should have warnings about missing files
        assert len(result.warnings) > 0
    
    def test_validate_spec_structure_missing_directory(self, file_manager):
        """Test spec structure validation with missing directory."""
        result = file_manager.validate_spec_structure("nonexistent-spec")
        
        assert not result.is_valid
        assert any(error.code == "SPEC_DIRECTORY_NOT_FOUND" for error in result.errors)
    
    def test_list_existing_specs_empty(self, file_manager):
        """Test listing specs when none exist."""
        specs = file_manager.list_existing_specs()
        assert len(specs) == 0
    
    def test_list_existing_specs_with_specs(self, file_manager, temp_workspace):
        """Test listing specs when some exist."""
        # Create multiple specs
        file_manager.create_spec_directory("spec-one")
        file_manager.create_spec_directory("spec-two")
        
        specs = file_manager.list_existing_specs()
        
        assert len(specs) == 2
        spec_names = [spec.feature_name for spec in specs]
        assert "spec-one" in spec_names
        assert "spec-two" in spec_names
    
    def test_discover_specs_success(self, file_manager, temp_workspace):
        """Test spec discovery functionality."""
        # Create specs with different states
        file_manager.create_spec_directory("complete-spec")
        file_manager.create_spec_directory("partial-spec")
        
        # Add some content to complete-spec
        file_manager.save_document("complete-spec", DocumentType.REQUIREMENTS, "# Requirements")
        file_manager.save_document("complete-spec", DocumentType.DESIGN, "# Design")
        file_manager.save_document("complete-spec", DocumentType.TASKS, "# Tasks")
        
        result = file_manager.discover_specs()
        
        assert len(result.specs) == 2
        assert result.total_count == 2
        
        # Find the complete spec and check progress
        complete_spec = next(spec for spec in result.specs if spec.feature_name == "complete-spec")
        assert complete_spec.progress == 1.0  # All files present
        
        partial_spec = next(spec for spec in result.specs if spec.feature_name == "partial-spec")
        assert partial_spec.progress == 0.0  # No files present
    
    def test_detect_file_corruption_clean(self, file_manager, temp_workspace):
        """Test corruption detection with clean files."""
        # Create spec with valid content
        file_manager.create_spec_directory("test-feature")
        file_manager.save_document("test-feature", DocumentType.REQUIREMENTS, "# Valid content")
        
        result = file_manager.detect_file_corruption("test-feature")
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_detect_file_corruption_missing_metadata(self, file_manager, temp_workspace):
        """Test corruption detection with missing metadata."""
        # Create spec directory manually without proper metadata
        spec_dir = Path(temp_workspace) / ".kiro/specs/test-feature"
        spec_dir.mkdir(parents=True)
        
        result = file_manager.detect_file_corruption("test-feature")
        
        assert not result.is_valid
        assert any(error.code == "METADATA_MISSING" for error in result.errors)
    
    def test_recover_spec_structure_missing_directory(self, file_manager, temp_workspace):
        """Test spec structure recovery with missing directory."""
        result = file_manager.recover_spec_structure("test-feature", create_missing=True)
        
        assert result.success
        assert "Created missing spec directory" in result.message
        
        # Verify directory and metadata were created
        spec_dir = Path(temp_workspace) / ".kiro/specs/test-feature"
        assert spec_dir.exists()
        
        metadata_path = spec_dir / ".spec-metadata.json"
        assert metadata_path.exists()
    
    def test_recover_spec_structure_corrupted_metadata(self, file_manager, temp_workspace):
        """Test spec structure recovery with corrupted metadata."""
        # Create spec directory with corrupted metadata
        spec_dir = Path(temp_workspace) / ".kiro/specs/test-feature"
        spec_dir.mkdir(parents=True)
        
        metadata_path = spec_dir / ".spec-metadata.json"
        with open(metadata_path, 'w') as f:
            f.write("invalid json content")
        
        result = file_manager.recover_spec_structure("test-feature", create_missing=True)
        
        assert result.success
        assert "Recreated metadata file" in result.message
        
        # Verify metadata is now valid
        with open(metadata_path, 'r') as f:
            metadata_data = json.load(f)
        
        metadata = SpecMetadata(**metadata_data)
        assert metadata.feature_name == "test-feature"
    
    def test_cleanup_spec_directory_success(self, file_manager, temp_workspace):
        """Test spec directory cleanup."""
        # Create spec with some temporary files
        file_manager.create_spec_directory("test-feature")
        spec_dir = Path(temp_workspace) / ".kiro/specs/test-feature"
        
        # Create temporary files
        (spec_dir / "temp.tmp").touch()
        (spec_dir / "backup.backup.123").touch()
        (spec_dir / ".DS_Store").touch()
        
        result = file_manager.cleanup_spec_directory("test-feature", remove_backups=True)
        
        assert result.success
        assert "temp.tmp" in result.message
        assert "backup.backup.123" in result.message
        assert ".DS_Store" in result.message
        
        # Verify files were removed
        assert not (spec_dir / "temp.tmp").exists()
        assert not (spec_dir / "backup.backup.123").exists()
        assert not (spec_dir / ".DS_Store").exists()
    
    def test_cleanup_spec_directory_not_found(self, file_manager):
        """Test cleanup of nonexistent spec directory."""
        result = file_manager.cleanup_spec_directory("nonexistent-spec")
        
        assert not result.success
        assert result.error_code == "SPEC_NOT_FOUND"
    
    def test_get_spec_file_structure(self, file_manager):
        """Test spec file structure generation."""
        structure = file_manager.get_spec_file_structure("test-feature")
        
        assert structure.spec_id == "test-feature"
        assert structure.base_path == ".kiro/specs/test-feature"
        assert structure.files["requirements"] == ".kiro/specs/test-feature/requirements.md"
        assert structure.files["design"] == ".kiro/specs/test-feature/design.md"
        assert structure.files["tasks"] == ".kiro/specs/test-feature/tasks.md"
        assert structure.files["metadata"] == ".kiro/specs/test-feature/.spec-metadata.json"
    
    def test_document_templates(self, file_manager):
        """Test document template generation."""
        for doc_type in DocumentType:
            template = file_manager._get_document_template(doc_type)
            assert len(template) > 0
            assert template.startswith("#")  # Should be markdown
    
    def test_permission_error_handling(self, file_manager, temp_workspace):
        """Test handling of permission errors."""
        # Create spec directory first
        file_manager.create_spec_directory("test-feature")
        
        # Mock open to raise PermissionError when writing the document file
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            result = file_manager.save_document("test-feature", DocumentType.REQUIREMENTS, "content")
        
        assert not result.success
        assert result.error_code == "PERMISSION_DENIED"
    
    def test_similarity_calculation(self, file_manager):
        """Test string similarity calculation."""
        # Test identical strings
        similarity = file_manager._calculate_similarity("test", "test")
        assert similarity == 1.0
        
        # Test completely different strings
        similarity = file_manager._calculate_similarity("abc", "xyz")
        assert similarity < 0.5
        
        # Test similar strings
        similarity = file_manager._calculate_similarity("user-auth", "user-auth-system")
        assert 0.5 < similarity < 1.0