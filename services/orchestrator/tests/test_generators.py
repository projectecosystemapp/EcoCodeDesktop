"""
Unit tests for document generation service components.

This module provides comprehensive testing for the requirements generator,
design generator, tasks generator, and document update manager.

Requirements addressed:
- 5.12: Unit tests for all document generation components
- Validation of EARS format, hierarchical numbering, and requirement traceability
"""

import pytest
import re
from datetime import datetime
from typing import Dict, Any, List

from eco_api.specs.generators import (
    RequirementsGenerator, DesignGenerator, TasksGenerator, DocumentUpdateManager,
    UserStory, AcceptanceCriterion, Requirement, EARSFormat,
    ResearchArea, ResearchFinding, Task
)
from eco_api.specs.models import ValidationResult, ValidationError, ValidationWarning


class TestRequirementsGenerator:
    """Test suite for RequirementsGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = RequirementsGenerator()
    
    def test_generate_requirements_document_basic(self):
        """Test basic requirements document generation."""
        feature_idea = "user authentication system with login and registration"
        
        result = self.generator.generate_requirements_document(feature_idea)
        
        # Check document structure
        assert "# Requirements Document" in result
        assert "## Introduction" in result
        assert "## Requirements" in result
        
        # Check for user stories
        assert "**User Story:**" in result
        assert "As a" in result
        assert "I want" in result
        assert "so that" in result
        
        # Check for EARS format
        ears_patterns = ["WHEN", "THEN", "SHALL", "IF"]
        for pattern in ears_patterns:
            assert pattern in result
    
    def test_extract_key_concepts(self):
        """Test key concept extraction from feature ideas."""
        feature_idea = "admin dashboard for managing user accounts and permissions"
        
        concepts = self.generator._extract_key_concepts(feature_idea)
        
        assert "admin" in concepts["actors"]
        assert "manage" in concepts["actions"]
        assert len(concepts["actors"]) > 0
        assert len(concepts["actions"]) > 0
    
    def test_generate_introduction(self):
        """Test introduction generation."""
        feature_idea = "task management system"
        concepts = {"actors": ["user", "admin"], "actions": ["create", "manage"]}
        
        intro = self.generator._generate_introduction(feature_idea, concepts)
        
        assert "task management" in intro.lower()
        assert "user" in intro
        assert "create" in intro or "manage" in intro
        assert len(intro) > 100  # Should be substantial
    
    def test_create_core_functional_requirement(self):
        """Test core functional requirement creation."""
        feature_idea = "file upload system"
        concepts = {"actors": ["user"], "actions": ["upload"]}
        
        requirement = self.generator._create_core_functional_requirement(feature_idea, concepts)
        
        assert requirement.id == "Requirement 1"
        assert "Core Functional Implementation" in requirement.title
        assert requirement.user_story.role == "user"
        assert "upload" in requirement.user_story.feature
        assert len(requirement.acceptance_criteria) >= 3
        
        # Check EARS format
        for criterion in requirement.acceptance_criteria:
            assert criterion.format_type in [EARSFormat.WHEN_THEN, EARSFormat.IF_THEN]
            assert "SHALL" in criterion.to_markdown()
    
    def test_validate_requirements_format_valid(self):
        """Test validation of properly formatted requirements."""
        valid_content = """# Requirements Document

## Introduction

This is a test feature for validation.

## Requirements

### Requirement 1: Test Requirement

**User Story:** As a user, I want to test functionality, so that I can validate the system

#### Acceptance Criteria

1.1. WHEN a user performs an action THEN the system SHALL respond appropriately
1.2. IF an error occurs THEN the system SHALL handle it gracefully
"""
        
        result = self.generator.validate_requirements_format(valid_content)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_requirements_format_missing_sections(self):
        """Test validation with missing required sections."""
        invalid_content = """# Requirements Document

Some content without proper sections.
"""
        
        result = self.generator.validate_requirements_format(invalid_content)
        
        assert not result.is_valid
        assert len(result.errors) > 0
        assert any("missing" in error.message.lower() for error in result.errors)
    
    def test_validate_requirements_format_no_user_stories(self):
        """Test validation with missing user stories."""
        content_no_stories = """# Requirements Document

## Introduction

Test introduction.

## Requirements

### Requirement 1: Test

Some content without user stories.
"""
        
        result = self.generator.validate_requirements_format(content_no_stories)
        
        assert not result.is_valid
        assert any("user stories" in error.message.lower() for error in result.errors)
    
    def test_user_story_to_markdown(self):
        """Test user story markdown conversion."""
        story = UserStory(
            role="developer",
            feature="write unit tests",
            benefit="I can ensure code quality"
        )
        
        markdown = story.to_markdown()
        
        assert "**User Story:**" in markdown
        assert "As a developer" in markdown
        assert "I want write unit tests" in markdown
        assert "so that I can ensure code quality" in markdown
    
    def test_acceptance_criterion_ears_formats(self):
        """Test different EARS format conversions."""
        # WHEN_THEN format
        when_then = AcceptanceCriterion(
            id="1.1",
            condition="user clicks button",
            action="the system",
            result="process the request",
            format_type=EARSFormat.WHEN_THEN
        )
        
        markdown = when_then.to_markdown()
        assert "1.1. WHEN user clicks button THEN the system SHALL process the request" == markdown
        
        # IF_THEN format
        if_then = AcceptanceCriterion(
            id="1.2",
            condition="input is invalid",
            action="the system",
            result="display error message",
            format_type=EARSFormat.IF_THEN
        )
        
        markdown = if_then.to_markdown()
        assert "1.2. IF input is invalid THEN the system SHALL display error message" == markdown


class TestDesignGenerator:
    """Test suite for DesignGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = DesignGenerator()
        self.sample_requirements = """# Requirements Document

## Introduction

Test feature for design generation.

## Requirements

### Requirement 1: Core Functionality

**User Story:** As a user, I want to use core features, so that I can accomplish my goals

#### Acceptance Criteria

1.1. WHEN user accesses feature THEN system SHALL provide functionality
1.2. IF errors occur THEN system SHALL handle gracefully
"""
    
    def test_generate_design_document_basic(self):
        """Test basic design document generation."""
        result = self.generator.generate_design_document(self.sample_requirements)
        
        # Check required sections
        required_sections = [
            "# Design Document",
            "## Overview",
            "## Architecture", 
            "## Components and Interfaces",
            "## Data Models",
            "## Error Handling",
            "## Testing Strategy"
        ]
        
        for section in required_sections:
            assert section in result
    
    def test_parse_requirements(self):
        """Test requirements parsing for design generation."""
        info = self.generator._parse_requirements(self.sample_requirements)
        
        assert info["feature_name"] == "Feature"  # Default when not specified
        assert len(info["user_stories"]) > 0
        assert len(info["acceptance_criteria"]) > 0
        assert "user" in info["actors"]
    
    def test_identify_research_areas(self):
        """Test research area identification."""
        requirements_info = {
            "actions": {"create", "manage", "validate"},
            "data_entities": {"user", "data", "document"}
        }
        
        research_context = self.generator._identify_research_areas(requirements_info)
        
        assert "areas" in research_context
        assert "findings" in research_context
        assert "technology_recommendations" in research_context
        assert len(research_context["areas"]) > 0
    
    def test_generate_overview(self):
        """Test overview section generation."""
        requirements_info = {
            "feature_name": "Test Feature",
            "actors": ["user", "admin"],
            "actions": ["create", "update", "delete"]
        }
        research_context = {"technology_recommendations": {}}
        
        overview = self.generator._generate_overview(requirements_info, research_context)
        
        assert "Test Feature" in overview
        assert "user" in overview
        assert "admin" in overview
        assert len(overview) > 200  # Should be substantial
    
    def test_generate_architecture(self):
        """Test architecture section generation."""
        requirements_info = {"feature_name": "Test Feature"}
        research_context = {
            "technology_recommendations": {
                "frontend": "React with TypeScript",
                "backend": "FastAPI with Python"
            },
            "architectural_patterns": [
                "Layered Architecture: Separate concerns",
                "Repository Pattern: Abstract data access"
            ]
        }
        
        architecture = self.generator._generate_architecture(requirements_info, research_context)
        
        assert "System Boundaries" in architecture
        assert "Technology Stack" in architecture
        assert "Architectural Patterns" in architecture
        assert "React with TypeScript" in architecture
        assert "FastAPI with Python" in architecture
    
    def test_validate_design_format_valid(self):
        """Test validation of properly formatted design document."""
        valid_design = """# Design Document

## Overview

Test overview content.

## Architecture

Test architecture content.

## Components and Interfaces

Test components content.

## Data Models

Test data models content.

## Error Handling

Test error handling content.

## Testing Strategy

Test testing strategy content.
"""
        
        result = self.generator.validate_design_format(valid_design)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_design_format_missing_sections(self):
        """Test validation with missing required sections."""
        invalid_design = """# Design Document

## Overview

Only overview section present.
"""
        
        result = self.generator.validate_design_format(invalid_design)
        
        assert not result.is_valid
        assert len(result.errors) > 0


class TestTasksGenerator:
    """Test suite for TasksGenerator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TasksGenerator()
        self.sample_requirements = """# Requirements Document

## Introduction

Test requirements for task generation.

## Requirements

### Requirement 1: Core Functionality

**User Story:** As a user, I want core functionality, so that I can accomplish goals

#### Acceptance Criteria

1.1. WHEN user performs action THEN system SHALL respond
1.2. IF error occurs THEN system SHALL handle gracefully

### Requirement 2: User Interface

**User Story:** As a user, I want intuitive interface, so that I can navigate easily

#### Acceptance Criteria

2.1. WHEN interface loads THEN system SHALL display clearly
2.2. WHEN user interacts THEN system SHALL provide feedback
"""
        
        self.sample_design = """# Design Document

## Overview

Test design for task generation.

## Architecture

System uses React frontend with FastAPI backend.

## Components and Interfaces

#### 1. User Interface Components
Main components for user interaction.

#### 2. Business Logic Components  
Core service classes for functionality.

## Data Models

Primary entity models with validation.

## Error Handling

Comprehensive error handling strategy.

## Testing Strategy

Unit and integration testing approach.
"""
    
    def test_generate_tasks_document_basic(self):
        """Test basic tasks document generation."""
        result = self.generator.generate_tasks_document(self.sample_requirements, self.sample_design)
        
        # Check document structure
        assert "# Implementation Plan" in result
        
        # Check for checkbox format
        checkbox_pattern = r"- \[ \] \d+(\.\d+)?\. .+"
        checkboxes = re.findall(checkbox_pattern, result)
        assert len(checkboxes) > 0
        
        # Check for requirement references
        assert "_Requirements:" in result
    
    def test_parse_requirements_for_tasks(self):
        """Test requirements parsing for task generation."""
        info = self.generator._parse_requirements_for_tasks(self.sample_requirements)
        
        assert len(info["requirements"]) == 2
        assert "core_functionality" in info["functional_areas"]
        assert "user_interface" in info["functional_areas"]
        
        # Check requirement structure
        req1 = info["requirements"][0]
        assert req1["id"] == "Requirement 1"
        assert "Core Functionality" in req1["title"]
        assert len(req1["criteria"]) == 2
    
    def test_parse_design_for_tasks(self):
        """Test design parsing for task generation."""
        info = self.generator._parse_design_for_tasks(self.sample_design)
        
        assert len(info["components"]) > 0
        assert "react" in info["technology_stack"].get("frontend", "")
        assert "fastapi" in info["technology_stack"].get("backend", "")
    
    def test_generate_task_hierarchy(self):
        """Test task hierarchy generation."""
        requirements_info = {
            "functional_areas": {"core_functionality", "user_interface", "security"},
            "requirements": [{"id": "Requirement 1", "title": "Test"}]
        }
        design_info = {
            "technology_stack": {"frontend": "react", "backend": "fastapi"},
            "components": [{"name": "TestComponent"}]
        }
        
        tasks = self.generator._generate_task_hierarchy(requirements_info, design_info)
        
        assert len(tasks) > 0
        
        # Check task structure
        for task in tasks:
            assert task.id is not None
            assert task.description is not None
            assert isinstance(task.details, list)
            assert isinstance(task.requirements, list)
            
            # Check subtasks if present
            if task.subtasks:
                for subtask in task.subtasks:
                    assert subtask.id.count('.') == 1  # Should be like "1.1", "1.2"
    
    def test_create_project_setup_task(self):
        """Test project setup task creation."""
        requirements_info = {"functional_areas": set()}
        design_info = {"technology_stack": {"frontend": "react", "backend": "fastapi"}}
        
        task = self.generator._create_project_setup_task(requirements_info, design_info)
        
        assert task.id == "1"
        assert "infrastructure" in task.description.lower()
        assert len(task.subtasks) >= 3
        assert len(task.requirements) > 0
        
        # Check subtask structure
        for subtask in task.subtasks:
            assert subtask.id.startswith("1.")
            assert len(subtask.details) > 0
    
    def test_task_to_markdown_lines(self):
        """Test task to markdown conversion."""
        task = Task(
            id="1",
            description="Test task",
            details=["Detail 1", "Detail 2"],
            requirements=["1.1", "1.2"],
            subtasks=[
                Task(
                    id="1.1",
                    description="Subtask",
                    details=["Subtask detail"],
                    requirements=["1.1"]
                )
            ]
        )
        
        lines = self.generator._task_to_markdown_lines(task)
        
        # Check main task
        assert "- [ ] 1. Test task" in lines
        assert "  - Detail 1" in lines
        assert "  - Detail 2" in lines
        assert "  - _Requirements: 1.1, 1.2_" in lines
        
        # Check subtask
        assert "  - [ ] 1.1. Subtask" in lines
        assert "    - Subtask detail" in lines
    
    def test_validate_tasks_format_valid(self):
        """Test validation of properly formatted tasks document."""
        valid_tasks = """# Implementation Plan

- [ ] 1. Set up project infrastructure
  - Create project structure
  - Configure build tools
  - _Requirements: 1.1, 1.2_

- [ ] 1.1 Create core components
  - Implement base classes
  - Add validation logic
  - _Requirements: 1.1_

- [ ] 2. Implement business logic
  - Create service classes
  - Add data processing
  - _Requirements: 2.1, 2.2_
"""
        
        result = self.generator.validate_tasks_format(valid_tasks)
        
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_tasks_format_non_coding_activities(self):
        """Test validation catches non-coding activities."""
        invalid_tasks = """# Implementation Plan

- [ ] 1. Conduct user testing
  - Gather user feedback
  - Deploy to production
  - _Requirements: 1.1_
"""
        
        result = self.generator.validate_tasks_format(invalid_tasks)
        
        assert not result.is_valid
        assert any("non-coding activity" in error.message.lower() for error in result.errors)


class TestDocumentUpdateManager:
    """Test suite for DocumentUpdateManager class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.manager = DocumentUpdateManager()
        self.sample_requirements = """# Requirements Document

## Introduction

Test requirements document for update testing.

## Requirements

### Requirement 1: Core Functionality

**User Story:** As a user, I want core functionality, so that I can accomplish goals

#### Acceptance Criteria

1.1. WHEN user performs action THEN system SHALL respond
1.2. IF error occurs THEN system SHALL handle gracefully
"""
        
        self.sample_design = """# Design Document

## Overview

Test design document.

## Architecture

System architecture details.

## Components and Interfaces

Component definitions.

## Data Models

Data model specifications.

## Error Handling

Error handling approach.

## Testing Strategy

Testing methodology.
"""
        
        self.sample_tasks = """# Implementation Plan

- [ ] 1. Set up infrastructure
  - Create project structure
  - _Requirements: 1.1_

- [ ] 2. Implement core logic
  - Create business services
  - _Requirements: 1.1, 1.2_
"""
    
    def test_update_requirements_document_add_requirement(self):
        """Test adding a new requirement."""
        changes = {
            "add_requirement": {
                "title": "New Security Requirement",
                "user_story": "**User Story:** As a user, I want secure access, so that my data is protected",
                "acceptance_criteria": "3.1. WHEN accessing system THEN user SHALL be authenticated"
            }
        }
        
        updated_content, changes_made = self.manager.update_requirements_document(
            self.sample_requirements, changes
        )
        
        assert "Requirement 2: New Security Requirement" in updated_content
        assert len(changes_made) == 1
        assert "Added Requirement 2" in changes_made[0]
    
    def test_update_requirements_document_modify_requirement(self):
        """Test modifying an existing requirement."""
        changes = {
            "modify_requirement": {
                "requirement_id": "Requirement 1",
                "title": "Modified Core Functionality",
                "body": "**User Story:** Modified user story content\n\n#### Acceptance Criteria\n\nModified criteria"
            }
        }
        
        updated_content, changes_made = self.manager.update_requirements_document(
            self.sample_requirements, changes
        )
        
        assert "Modified Core Functionality" in updated_content
        assert len(changes_made) == 1
        assert "Modified Requirement 1" in changes_made[0]
    
    def test_update_design_document_section(self):
        """Test updating a design document section."""
        changes = {
            "update_section": {
                "section": "Overview",
                "content": "Updated overview content with new information."
            }
        }
        
        updated_content, changes_made = self.manager.update_design_document(
            self.sample_design, changes, self.sample_requirements
        )
        
        assert "Updated overview content" in updated_content
        assert len(changes_made) >= 1
        assert any("Updated Overview section" in change for change in changes_made)
    
    def test_update_tasks_document_add_task(self):
        """Test adding a new task."""
        changes = {
            "add_task": {
                "id": "3",
                "description": "Implement security features",
                "details": ["Add authentication", "Implement authorization"],
                "requirements": ["3.1", "3.2"]
            }
        }
        
        updated_content, changes_made = self.manager.update_tasks_document(
            self.sample_tasks, changes, self.sample_requirements, self.sample_design
        )
        
        assert "- [ ] 3. Implement security features" in updated_content
        assert "Add authentication" in updated_content
        assert "_Requirements: 3.1, 3.2_" in updated_content
        assert len(changes_made) >= 1
    
    def test_update_task_status(self):
        """Test updating task completion status."""
        changes = {
            "update_task_status": {
                "task_id": "1",
                "completed": True
            }
        }
        
        updated_content, changes_made = self.manager.update_tasks_document(
            self.sample_tasks, changes, self.sample_requirements, self.sample_design
        )
        
        assert "- [x] 1. Set up infrastructure" in updated_content
        assert len(changes_made) >= 1
        assert any("completed" in change for change in changes_made)
    
    def test_validate_cross_document_consistency(self):
        """Test cross-document consistency validation."""
        # Create inconsistent documents
        inconsistent_design = """# Design Document

## Overview

Design that doesn't address requirements.

## Architecture

Missing sections.
"""
        
        result = self.manager.validate_cross_document_consistency(
            self.sample_requirements, inconsistent_design, self.sample_tasks
        )
        
        # Should detect inconsistencies
        assert len(result.errors) > 0 or len(result.warnings) > 0
    
    def test_parse_current_requirements(self):
        """Test parsing current requirements structure."""
        info = self.manager._parse_current_requirements(self.sample_requirements)
        
        assert len(info["requirements"]) == 1
        assert info["requirement_count"] == 1
        assert "Test requirements document" in info["introduction"]
        
        req = info["requirements"][0]
        assert req["id"] == "Requirement 1"
        assert "Core Functionality" in req["title"]
    
    def test_validate_task_requirements_traceability(self):
        """Test task-requirements traceability validation."""
        # Create tasks with invalid references
        invalid_tasks = """# Implementation Plan

- [ ] 1. Test task
  - Some details
  - _Requirements: 9.9, 10.1_
"""
        
        issues = self.manager._validate_task_requirements_traceability(
            invalid_tasks, self.sample_requirements
        )
        
        assert len(issues) > 0
        assert any("invalid requirement" in issue.lower() for issue in issues)


class TestIntegration:
    """Integration tests for document generators working together."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.req_generator = RequirementsGenerator()
        self.design_generator = DesignGenerator()
        self.tasks_generator = TasksGenerator()
        self.update_manager = DocumentUpdateManager()
    
    def test_full_document_generation_workflow(self):
        """Test complete workflow from feature idea to tasks."""
        feature_idea = "project management system with task tracking and user collaboration"
        
        # Generate requirements
        requirements = self.req_generator.generate_requirements_document(feature_idea)
        assert len(requirements) > 500  # Should be substantial
        
        # Generate design from requirements
        design = self.design_generator.generate_design_document(requirements)
        assert len(design) > 1000  # Should be comprehensive
        
        # Generate tasks from requirements and design
        tasks = self.tasks_generator.generate_tasks_document(requirements, design)
        assert len(tasks) > 800  # Should be detailed
        
        # Validate all documents
        req_validation = self.req_generator.validate_requirements_format(requirements)
        design_validation = self.design_generator.validate_design_format(design)
        tasks_validation = self.tasks_generator.validate_tasks_format(tasks)
        
        assert req_validation.is_valid
        assert design_validation.is_valid
        assert tasks_validation.is_valid
        
        # Validate cross-document consistency
        consistency = self.update_manager.validate_cross_document_consistency(
            requirements, design, tasks
        )
        
        # Should have minimal issues for generated documents
        assert len(consistency.errors) <= 2  # Allow for minor inconsistencies
    
    def test_document_update_workflow(self):
        """Test document update and consistency maintenance."""
        # Start with basic documents
        requirements = self.req_generator.generate_requirements_document("simple feature")
        design = self.design_generator.generate_design_document(requirements)
        
        # Update requirements
        req_changes = {
            "add_requirement": {
                "title": "Additional Security",
                "user_story": "**User Story:** As a user, I want security, so that I'm protected",
                "acceptance_criteria": "2.1. WHEN accessing THEN system SHALL authenticate"
            }
        }
        
        updated_req, req_changes_made = self.update_manager.update_requirements_document(
            requirements, req_changes
        )
        
        # Update design to reflect new requirements
        design_changes = {
            "update_section": {
                "section": "Architecture",
                "content": "Updated architecture with security considerations."
            }
        }
        
        updated_design, design_changes_made = self.update_manager.update_design_document(
            design, design_changes, updated_req
        )
        
        # Verify changes were applied
        assert len(req_changes_made) > 0
        assert len(design_changes_made) > 0
        assert "Additional Security" in updated_req
        assert "security considerations" in updated_design


if __name__ == "__main__":
    pytest.main([__file__, "-v"])