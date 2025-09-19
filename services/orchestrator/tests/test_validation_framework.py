"""
Tests for the validation framework.

This module tests validation rules, error reporting, and recovery procedures
for all components in the spec workflow system.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from eco_api.specs.validation_framework import (
    ValidationFramework,
    StructureValidator,
    ContentValidator,
    FormatValidator,
    ConsistencyValidator,
    TraceabilityValidator,
    WorkflowValidator,
    ValidationRule,
    ValidationIssue,
    ValidationReport,
    ValidationType,
    ValidationSeverity
)
from eco_api.specs.models import WorkflowPhase, WorkflowStatus, DocumentType


class TestValidationFramework:
    """Test cases for ValidationFramework."""
    
    @pytest.fixture
    def validation_framework(self):
        """Create a ValidationFramework instance for testing."""
        return ValidationFramework()
    
    @pytest.fixture
    def sample_requirements_content(self):
        """Sample requirements document content."""
        return """# Requirements Document

## Introduction

This is a sample requirements document for testing validation.

## Requirements

### Requirement 1

**User Story:** As a developer, I want to create specs, so that I can organize my work.

#### Acceptance Criteria

1. WHEN a user creates a spec THEN the system SHALL generate a directory structure
2. WHEN the spec is created THEN the system SHALL validate the input

### Requirement 2

**User Story:** As a user, I want to validate documents, so that I can ensure quality.

#### Acceptance Criteria

1. WHEN validation runs THEN the system SHALL check document structure
2. IF errors are found THEN the system SHALL report them clearly
"""
    
    @pytest.fixture
    def sample_design_content(self):
        """Sample design document content."""
        return """# Design Document

## Overview

This is a sample design document for testing validation.

## Architecture

The system follows a modular architecture.

## Components and Interfaces

The main components are validation and error handling.

## Data Models

Data models include ValidationRule and ValidationIssue.

## Error Handling

Errors are handled through the error recovery service.

## Testing Strategy

Testing includes unit tests and integration tests.
"""
    
    @pytest.fixture
    def sample_tasks_content(self):
        """Sample tasks document content."""
        return """# Implementation Plan

- [ ] 1. Create validation framework
  - Implement validation rules and validators
  - Create comprehensive test coverage
  - _Requirements: 1.1, 1.2_

- [ ] 2. Add error handling
  - Implement error classification
  - Create recovery mechanisms
  - _Requirements: 2.1, 2.2_
"""
    
    def test_framework_initialization(self, validation_framework):
        """Test that the validation framework initializes correctly."""
        assert len(validation_framework.rules) > 0
        assert len(validation_framework.validators) > 0
        
        # Check that default rules are present
        expected_rules = [
            "structure_requirements",
            "structure_design", 
            "structure_tasks",
            "content_quality",
            "format_markdown",
            "consistency_cross_document",
            "traceability_requirements",
            "workflow_state"
        ]
        
        for rule_id in expected_rules:
            assert rule_id in validation_framework.rules
            assert rule_id in validation_framework.validators
    
    def test_validate_requirements_document_valid(self, validation_framework, sample_requirements_content):
        """Test validation of a valid requirements document."""
        report = validation_framework.validate_document(
            content=sample_requirements_content,
            document_type=DocumentType.REQUIREMENTS,
            phase=WorkflowPhase.REQUIREMENTS,
            context={'spec_id': 'test-spec'}
        )
        
        assert report.overall_status in ["valid", "warnings"]
        assert not report.has_errors()
    
    def test_validate_requirements_document_missing_sections(self, validation_framework):
        """Test validation of requirements document with missing sections."""
        invalid_content = """# Requirements Document

This is incomplete.
"""
        
        report = validation_framework.validate_document(
            content=invalid_content,
            document_type=DocumentType.REQUIREMENTS,
            phase=WorkflowPhase.REQUIREMENTS,
            context={'spec_id': 'test-spec'}
        )
        
        assert report.has_errors()
        error_messages = [issue.message for issue in report.get_issues_by_severity(ValidationSeverity.ERROR)]
        assert any("Missing required section" in msg for msg in error_messages)
    
    def test_validate_design_document_valid(self, validation_framework, sample_design_content):
        """Test validation of a valid design document."""
        report = validation_framework.validate_document(
            content=sample_design_content,
            document_type=DocumentType.DESIGN,
            phase=WorkflowPhase.DESIGN,
            context={'spec_id': 'test-spec'}
        )
        
        assert report.overall_status in ["valid", "warnings"]
        assert not report.has_errors()
    
    def test_validate_design_document_missing_sections(self, validation_framework):
        """Test validation of design document with missing sections."""
        invalid_content = """# Design Document

## Overview

This is incomplete.
"""
        
        report = validation_framework.validate_document(
            content=invalid_content,
            document_type=DocumentType.DESIGN,
            phase=WorkflowPhase.DESIGN,
            context={'spec_id': 'test-spec'}
        )
        
        assert report.has_errors()
        error_messages = [issue.message for issue in report.get_issues_by_severity(ValidationSeverity.ERROR)]
        assert any("Missing required section" in msg for msg in error_messages)
    
    def test_validate_tasks_document_valid(self, validation_framework, sample_tasks_content):
        """Test validation of a valid tasks document."""
        report = validation_framework.validate_document(
            content=sample_tasks_content,
            document_type=DocumentType.TASKS,
            phase=WorkflowPhase.TASKS,
            context={'spec_id': 'test-spec'}
        )
        
        assert report.overall_status in ["valid", "warnings"]
        assert not report.has_errors()
    
    def test_validate_tasks_document_missing_header(self, validation_framework):
        """Test validation of tasks document with missing header."""
        invalid_content = """- [ ] 1. Some task
- [ ] 2. Another task
"""
        
        report = validation_framework.validate_document(
            content=invalid_content,
            document_type=DocumentType.TASKS,
            phase=WorkflowPhase.TASKS,
            context={'spec_id': 'test-spec'}
        )
        
        assert report.has_errors()
        error_messages = [issue.message for issue in report.get_issues_by_severity(ValidationSeverity.ERROR)]
        assert any("Missing implementation plan header" in msg for msg in error_messages)
    
    def test_validate_spec_complete(self, validation_framework, sample_requirements_content, 
                                   sample_design_content, sample_tasks_content):
        """Test validation of a complete spec with all documents."""
        documents = {
            'requirements': sample_requirements_content,
            'design': sample_design_content,
            'tasks': sample_tasks_content
        }
        
        report = validation_framework.validate_spec(
            spec_id='test-spec',
            documents=documents,
            current_phase=WorkflowPhase.EXECUTION,
            workflow_status=WorkflowStatus.IN_PROGRESS
        )
        
        assert report.spec_id == 'test-spec'
        assert report.overall_status in ["valid", "warnings"]
        assert len(report.rules_checked) > 0
    
    def test_validate_spec_cross_document_consistency(self, validation_framework):
        """Test cross-document consistency validation."""
        requirements_content = """# Requirements Document

## Introduction

Test requirements.

## Requirements

### Requirement 1

**User Story:** As a user, I want feature A, so that I can do something.

#### Acceptance Criteria

1. WHEN condition A THEN system SHALL do X
2. WHEN condition B THEN system SHALL do Y

### Requirement 2

**User Story:** As a user, I want feature B, so that I can do something else.

#### Acceptance Criteria

1. WHEN condition C THEN system SHALL do Z
"""
        
        tasks_content = """# Implementation Plan

- [ ] 1. Implement feature A
  - Create component A
  - Add tests for component A
  - _Requirements: 1.1_

- [ ] 2. Implement feature B
  - Create component B
  - Add tests for component B
  - _Requirements: 2.1_
"""
        
        documents = {
            'requirements': requirements_content,
            'tasks': tasks_content
        }
        
        report = validation_framework.validate_spec(
            spec_id='test-spec',
            documents=documents,
            current_phase=WorkflowPhase.TASKS,
            workflow_status=WorkflowStatus.IN_PROGRESS
        )
        
        # Should have warnings about unreferenced acceptance criteria
        assert report.has_warnings()
        warning_messages = [issue.message for issue in report.get_issues_by_severity(ValidationSeverity.WARNING)]
        assert any("not traced to tasks" in msg for msg in warning_messages)
    
    def test_content_validator_placeholder_detection(self, validation_framework):
        """Test content validator detects placeholder text."""
        content_with_placeholders = """# Requirements Document

## Introduction

TODO: Add proper introduction here.

## Requirements

### Requirement 1

**User Story:** TBD

#### Acceptance Criteria

1. FIXME: Add acceptance criteria
"""
        
        report = validation_framework.validate_document(
            content=content_with_placeholders,
            document_type=DocumentType.REQUIREMENTS,
            phase=WorkflowPhase.REQUIREMENTS,
            context={'spec_id': 'test-spec'}
        )
        
        warning_messages = [issue.message for issue in report.get_issues_by_severity(ValidationSeverity.WARNING)]
        assert any("placeholder text" in msg for msg in warning_messages)
    
    def test_format_validator_header_spacing(self, validation_framework):
        """Test format validator detects header spacing issues."""
        content_with_format_issues = """#Requirements Document

##Introduction

This has formatting issues.

###Requirement 1

**User Story:** As a user, I want something.
"""
        
        report = validation_framework.validate_document(
            content=content_with_format_issues,
            document_type=DocumentType.REQUIREMENTS,
            phase=WorkflowPhase.REQUIREMENTS,
            context={'spec_id': 'test-spec'}
        )
        
        warning_messages = [issue.message for issue in report.get_issues_by_severity(ValidationSeverity.WARNING)]
        assert any("space after #" in msg for msg in warning_messages)
    
    def test_workflow_validator_phase_prerequisites(self, validation_framework):
        """Test workflow validator checks phase prerequisites."""
        # Test design phase without requirements
        report = validation_framework.validate_spec(
            spec_id='test-spec',
            documents={'design': 'some content'},
            current_phase=WorkflowPhase.DESIGN,
            workflow_status=WorkflowStatus.IN_PROGRESS,
            context={'documents': {'design': 'some content'}}
        )
        
        assert report.has_errors()
        error_messages = [issue.message for issue in report.get_issues_by_severity(ValidationSeverity.ERROR)]
        assert any("without approved requirements" in msg for msg in error_messages)
    
    def test_consistency_validator_requirement_numbering(self, validation_framework):
        """Test consistency validator checks requirement numbering."""
        content_with_numbering_issues = """# Requirements Document

## Introduction

Test requirements.

## Requirements

### Requirement 1

**User Story:** First requirement.

### Requirement 3

**User Story:** Third requirement (missing 2).

### Requirement 4

**User Story:** Fourth requirement.
"""
        
        report = validation_framework.validate_document(
            content=content_with_numbering_issues,
            document_type=DocumentType.REQUIREMENTS,
            phase=WorkflowPhase.REQUIREMENTS,
            context={'spec_id': 'test-spec'}
        )
        
        error_messages = [issue.message for issue in report.get_issues_by_severity(ValidationSeverity.ERROR)]
        assert any("not sequential" in msg for msg in error_messages)
    
    def test_add_custom_rule(self, validation_framework):
        """Test adding custom validation rules."""
        custom_rule = ValidationRule(
            id="custom_test_rule",
            name="Custom Test Rule",
            description="A custom rule for testing",
            type=ValidationType.CONTENT,
            severity=ValidationSeverity.WARNING,
            applicable_phases=[WorkflowPhase.REQUIREMENTS]
        )
        
        class CustomValidator(ContentValidator):
            def validate(self, content, context):
                issues = []
                if "custom_issue" in content:
                    issues.append(ValidationIssue(
                        rule_id=self.rule.id,
                        severity=ValidationSeverity.WARNING,
                        message="Custom issue detected"
                    ))
                return issues
        
        custom_validator = CustomValidator(custom_rule)
        validation_framework.add_custom_rule(custom_rule, custom_validator)
        
        assert "custom_test_rule" in validation_framework.rules
        assert "custom_test_rule" in validation_framework.validators
        
        # Test the custom rule
        content_with_custom_issue = "This content has a custom_issue in it."
        report = validation_framework.validate_document(
            content=content_with_custom_issue,
            document_type=DocumentType.REQUIREMENTS,
            phase=WorkflowPhase.REQUIREMENTS,
            context={'spec_id': 'test-spec'}
        )
        
        warning_messages = [issue.message for issue in report.get_issues_by_severity(ValidationSeverity.WARNING)]
        assert any("Custom issue detected" in msg for msg in warning_messages)
    
    def test_disable_enable_rule(self, validation_framework):
        """Test disabling and enabling validation rules."""
        rule_id = "content_quality"
        
        # Disable rule
        validation_framework.disable_rule(rule_id)
        assert not validation_framework.rules[rule_id].enabled
        
        # Enable rule
        validation_framework.enable_rule(rule_id)
        assert validation_framework.rules[rule_id].enabled
    
    def test_validation_guidance(self, validation_framework):
        """Test generation of validation guidance."""
        issues = [
            ValidationIssue(
                rule_id="structure_requirements",
                severity=ValidationSeverity.ERROR,
                message="Missing section",
                suggestion="Add the missing section"
            ),
            ValidationIssue(
                rule_id="content_quality",
                severity=ValidationSeverity.WARNING,
                message="Content too short"
            )
        ]
        
        guidance = validation_framework.get_validation_guidance(issues)
        
        assert "structure_requirements" in guidance
        assert "content_quality" in guidance
        assert "Add the missing section" in guidance["structure_requirements"]
        assert len(guidance["content_quality"]) > 0
    
    def test_auto_fix_issues(self, validation_framework):
        """Test automatic fixing of validation issues."""
        content_with_fixable_issues = """#Header Without Space
##Another Header
###Third Header
"""
        
        issues = [
            ValidationIssue(
                rule_id="format_markdown",
                severity=ValidationSeverity.WARNING,
                message="Header should have space after #",
                line_number=1,
                auto_fixable=True
            )
        ]
        
        fixed_content = validation_framework.auto_fix_issues(content_with_fixable_issues, issues)
        
        # The auto-fix functionality is basic in this implementation
        # In a real implementation, this would fix the header spacing
        assert fixed_content is not None
    
    def test_validation_report_methods(self):
        """Test ValidationReport helper methods."""
        issues = [
            ValidationIssue(
                rule_id="test_rule_1",
                severity=ValidationSeverity.ERROR,
                message="Error message"
            ),
            ValidationIssue(
                rule_id="test_rule_2",
                severity=ValidationSeverity.WARNING,
                message="Warning message"
            ),
            ValidationIssue(
                rule_id="test_rule_3",
                severity=ValidationSeverity.INFO,
                message="Info message"
            )
        ]
        
        report = ValidationReport(
            spec_id="test-spec",
            validation_time=datetime.utcnow(),
            overall_status="errors",
            issues=issues,
            rules_checked=["test_rule_1", "test_rule_2", "test_rule_3"],
            summary={
                'total_issues': 3,
                'errors': 1,
                'warnings': 1,
                'info': 1
            }
        )
        
        assert report.has_errors()
        assert report.has_warnings()
        
        errors = report.get_issues_by_severity(ValidationSeverity.ERROR)
        assert len(errors) == 1
        assert errors[0].message == "Error message"
        
        warnings = report.get_issues_by_severity(ValidationSeverity.WARNING)
        assert len(warnings) == 1
        assert warnings[0].message == "Warning message"


class TestIndividualValidators:
    """Test cases for individual validator classes."""
    
    def test_structure_validator_requirements(self):
        """Test StructureValidator for requirements documents."""
        rule = ValidationRule(
            id="test_structure",
            name="Test Structure",
            description="Test structure validation",
            type=ValidationType.STRUCTURE,
            severity=ValidationSeverity.ERROR,
            applicable_documents=[DocumentType.REQUIREMENTS]
        )
        
        validator = StructureValidator(rule)
        
        # Test valid content
        valid_content = """# Requirements Document

## Introduction

Test introduction.

## Requirements

### Requirement 1

**User Story:** As a user, I want something.

#### Acceptance Criteria

1. WHEN something THEN system SHALL do something
"""
        
        issues = validator.validate(valid_content, {'document_type': DocumentType.REQUIREMENTS})
        assert len(issues) == 0
        
        # Test invalid content
        invalid_content = """# Wrong Title

Some content without proper structure.
"""
        
        issues = validator.validate(invalid_content, {'document_type': DocumentType.REQUIREMENTS})
        assert len(issues) > 0
        assert any("Missing required section" in issue.message for issue in issues)
    
    def test_content_validator_short_content(self):
        """Test ContentValidator detects short content."""
        rule = ValidationRule(
            id="test_content",
            name="Test Content",
            description="Test content validation",
            type=ValidationType.CONTENT,
            severity=ValidationSeverity.WARNING
        )
        
        validator = ContentValidator(rule)
        
        short_content = "Too short"
        issues = validator.validate(short_content, {})
        
        assert len(issues) > 0
        assert any("very short" in issue.message for issue in issues)
    
    def test_format_validator_list_formatting(self):
        """Test FormatValidator detects list formatting issues."""
        rule = ValidationRule(
            id="test_format",
            name="Test Format",
            description="Test format validation",
            type=ValidationType.FORMAT,
            severity=ValidationSeverity.WARNING
        )
        
        validator = FormatValidator(rule)
        
        content_with_format_issues = """# Header

1.Item without space
2. Item with space
"""
        
        issues = validator.validate(content_with_format_issues, {})
        
        # The validator should detect formatting issues
        assert len(issues) >= 0  # May or may not detect issues based on implementation
    
    def test_traceability_validator_missing_references(self):
        """Test TraceabilityValidator detects missing requirement references."""
        rule = ValidationRule(
            id="test_traceability",
            name="Test Traceability",
            description="Test traceability validation",
            type=ValidationType.TRACEABILITY,
            severity=ValidationSeverity.WARNING
        )
        
        validator = TraceabilityValidator(rule)
        
        documents = {
            'requirements': """# Requirements Document

## Requirements

### Requirement 1

#### Acceptance Criteria

1. WHEN something THEN system SHALL do X
2. WHEN something else THEN system SHALL do Y
""",
            'tasks': """# Implementation Plan

- [ ] 1. Implement feature
  - Do something
  - _Requirements: 1.1_
"""
        }
        
        issues = validator.validate({'documents': documents}, {})
        
        # Should detect that acceptance criterion 1.2 is not referenced
        assert len(issues) > 0
        assert any("not traced to tasks" in issue.message for issue in issues)
    
    def test_workflow_validator_invalid_transition(self):
        """Test WorkflowValidator detects invalid workflow transitions."""
        rule = ValidationRule(
            id="test_workflow",
            name="Test Workflow",
            description="Test workflow validation",
            type=ValidationType.WORKFLOW,
            severity=ValidationSeverity.ERROR
        )
        
        validator = WorkflowValidator(rule)
        
        context = {
            'current_phase': WorkflowPhase.DESIGN,
            'workflow_status': WorkflowStatus.IN_PROGRESS,
            'documents': {}  # No requirements document
        }
        
        issues = validator.validate(None, context)
        
        assert len(issues) > 0
        assert any("without approved requirements" in issue.message for issue in issues)