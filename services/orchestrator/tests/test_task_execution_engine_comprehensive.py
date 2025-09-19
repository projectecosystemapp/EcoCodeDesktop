"""
Comprehensive unit tests for TaskExecutionEngine with mock contexts.

This module provides extensive testing for task execution logic with all
external dependencies mocked to ensure isolated unit testing.

Requirements addressed:
- 4.13: Task execution testing and validation
- 6.9, 6.12: Task execution integration tests with mock contexts
- All task execution requirements - validation through comprehensive testing
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List

from eco_api.specs.task_execution_engine import (
    TaskExecutionEngine, Task, ExecutionContext, TaskResult, ProjectStructure, CodeContext
)
from eco_api.specs.models import (
    TaskStatus, DocumentType, ValidationResult, ValidationError, ValidationWarning,
    SpecDocument, SpecMetadata, WorkflowPhase, WorkflowStatus, DocumentMetadata
)
from eco_api.specs.file_manager import FileSystemManager


class TestTaskExecutionEngineUnitTests:
    """Comprehensive unit tests for TaskExecutionEngine with mocked dependencies."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_file_manager(self):
        """Create a mock FileSystemManager."""
        manager = Mock(spec=FileSystemManager)
        
        # Default successful responses
        manager.validate_spec_structure.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
        manager.load_document.return_value = (Mock(), Mock(success=True))
        manager.save_document.return_value = Mock(success=True)
        manager._load_spec_metadata.return_value = Mock()
        
        return manager
    
    @pytest.fixture
    def mock_execution_context(self):
        """Create a comprehensive mock execution context."""
        return ExecutionContext(
            requirements_content="""# Requirements Document

## Introduction

Test feature for comprehensive task execution testing.

## Requirements

### Requirement 1: Core Functionality

**User Story:** As a user, I want core functionality, so that I can accomplish my goals

#### Acceptance Criteria

1.1. WHEN user performs action THEN system SHALL respond appropriately
1.2. IF error occurs THEN system SHALL handle gracefully
1.3. WHEN data is processed THEN system SHALL validate input

### Requirement 2: User Interface

**User Story:** As a user, I want intuitive interface, so that I can navigate easily

#### Acceptance Criteria

2.1. WHEN interface loads THEN system SHALL display clearly
2.2. WHEN user interacts THEN system SHALL provide feedback
2.3. IF user makes error THEN system SHALL guide correction

### Requirement 3: Data Management

**User Story:** As a user, I want reliable data handling, so that my information is safe

#### Acceptance Criteria

3.1. WHEN data is saved THEN system SHALL persist securely
3.2. WHEN data is retrieved THEN system SHALL return accurately
3.3. IF data is corrupted THEN system SHALL recover gracefully
""",
            design_content="""# Design Document

## Overview

Comprehensive system design with multiple components and clear architecture.

## Architecture

### System Boundaries
- Frontend: React with TypeScript
- Backend: FastAPI with Python
- Database: PostgreSQL with Redis cache
- External APIs: Third-party integrations

### Technology Stack
- Frontend Framework: React 18+ with TypeScript
- Backend Framework: FastAPI with Pydantic
- Database: PostgreSQL 14+ with SQLAlchemy ORM
- Caching: Redis for session and data caching
- Authentication: JWT with refresh tokens

## Components and Interfaces

#### 1. User Interface Layer
React components with TypeScript for type safety and maintainability.

#### 2. API Gateway
FastAPI application handling HTTP requests and routing.

#### 3. Business Logic Layer
Service classes implementing core business functionality.

#### 4. Data Access Layer
Repository pattern with SQLAlchemy for database operations.

#### 5. External Integration Layer
Adapters for third-party service integrations.

## Data Models

### User Model
- id: UUID primary key
- email: Unique email address
- password_hash: Bcrypt hashed password
- created_at: Timestamp
- updated_at: Timestamp

### Profile Model
- user_id: Foreign key to User
- first_name: User's first name
- last_name: User's last name
- preferences: JSON field for user preferences

## Error Handling

### Error Categories
1. Validation Errors (400)
2. Authentication Errors (401)
3. Authorization Errors (403)
4. Not Found Errors (404)
5. Server Errors (500)

### Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}
```

## Testing Strategy

### Unit Testing
- Component isolation with mocked dependencies
- Business logic testing with comprehensive scenarios
- Data model validation testing

### Integration Testing
- API endpoint testing with test database
- Database integration with transaction rollback
- External service integration with mocked responses

### End-to-End Testing
- User workflow testing with Playwright
- Performance testing with load scenarios
- Security testing with penetration testing tools
""",
            tasks_content="""# Implementation Plan

- [ ] 1. Set up project infrastructure and development environment
  - Create project directory structure with proper organization
  - Configure package management and dependency installation
  - Set up development tools and code quality checks
  - _Requirements: 1.1, 2.1, 3.1_

- [ ] 1.1 Initialize project structure
  - Create frontend and backend directory structure
  - Set up package.json and pyproject.toml configuration files
  - Configure TypeScript and Python development environments
  - _Requirements: 1.1_

- [ ] 1.2 Configure development tools
  - Set up ESLint, Prettier, and TypeScript configuration
  - Configure Python linting with Ruff and type checking with MyPy
  - Set up pre-commit hooks for code quality enforcement
  - _Requirements: 1.1, 2.1_

- [ ] 2. Implement core data models and database schema
  - Design and create database schema with proper relationships
  - Implement SQLAlchemy models with validation and constraints
  - Create database migration scripts and seed data
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 2.1 Create User and Profile models
  - Implement User model with authentication fields
  - Create Profile model with user relationship
  - Add model validation and custom methods
  - _Requirements: 3.1, 3.2_

- [ ] 2.2 Set up database migrations
  - Configure Alembic for database migrations
  - Create initial migration scripts for all models
  - Implement database seeding for development data
  - _Requirements: 3.1, 3.3_

- [ ] 3. Build authentication and authorization system
  - Implement JWT token generation and validation
  - Create user registration and login endpoints
  - Add role-based access control and permissions
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 3.1 Implement JWT authentication
  - Create JWT token service with signing and verification
  - Implement token refresh mechanism for security
  - Add middleware for request authentication
  - _Requirements: 1.1, 1.2_

- [ ] 3.2 Create user management endpoints
  - Build registration endpoint with email verification
  - Implement login endpoint with credential validation
  - Add password reset functionality with secure tokens
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 4. Develop frontend user interface components
  - Create React components with TypeScript interfaces
  - Implement responsive design with CSS modules
  - Add form validation and error handling
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 4.1 Build authentication UI components
  - Create login and registration forms with validation
  - Implement password strength indicators and requirements
  - Add loading states and error message displays
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 4.2 Implement user dashboard interface
  - Create main dashboard layout with navigation
  - Build user profile management interface
  - Add settings and preferences management
  - _Requirements: 2.1, 2.2_

- [ ] 5. Create comprehensive testing suite
  - Write unit tests for all components and services
  - Implement integration tests for API endpoints
  - Add end-to-end tests for critical user workflows
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3_

- [ ] 5.1 Write backend unit tests
  - Test all service classes with mocked dependencies
  - Validate data models and business logic
  - Test error handling and edge cases
  - _Requirements: 1.1, 1.2, 1.3, 3.1, 3.2, 3.3_

- [ ] 5.2 Implement frontend component tests
  - Test React components with React Testing Library
  - Validate user interactions and state management
  - Test form validation and error handling
  - _Requirements: 2.1, 2.2, 2.3_
""",
            project_structure=ProjectStructure(
                root_path="/test/workspace",
                directories=[
                    "src", "tests", "docs", "scripts",
                    "src/frontend", "src/backend", "src/shared",
                    "src/frontend/components", "src/frontend/pages", "src/frontend/hooks",
                    "src/backend/api", "src/backend/models", "src/backend/services",
                    "tests/unit", "tests/integration", "tests/e2e"
                ],
                files=[
                    "package.json", "pyproject.toml", "README.md", ".gitignore",
                    "src/frontend/App.tsx", "src/frontend/index.tsx",
                    "src/backend/main.py", "src/backend/config.py",
                    "tests/conftest.py", "tests/pytest.ini"
                ],
                package_files=["package.json", "pyproject.toml"]
            ),
            existing_code=CodeContext(
                existing_files={
                    "src/backend/main.py": "# FastAPI main application",
                    "src/frontend/App.tsx": "// React main component",
                    "src/backend/config.py": "# Configuration settings",
                    "src/shared/types.ts": "// Shared TypeScript types"
                },
                imports=[
                    "from fastapi import FastAPI",
                    "import React from 'react'",
                    "from sqlalchemy import Column, Integer, String",
                    "import axios from 'axios'"
                ],
                classes=[
                    "FastAPI", "React.Component", "SQLAlchemy.Model", "Pydantic.BaseModel"
                ],
                functions=[
                    "create_app", "authenticate_user", "hash_password", "generate_token"
                ]
            ),
            spec_metadata=SpecMetadata(
                id="comprehensive-test-feature",
                feature_name="comprehensive-test-feature",
                version="1.0.0",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                current_phase=WorkflowPhase.EXECUTION,
                status=WorkflowStatus.IN_PROGRESS,
                checksum={}
            )
        )
    
    @pytest.fixture
    def task_engine(self, temp_workspace, mock_file_manager):
        """Create TaskExecutionEngine with mocked dependencies."""
        with patch('eco_api.specs.task_execution_engine.FileSystemManager', return_value=mock_file_manager):
            return TaskExecutionEngine(temp_workspace)
    
    @pytest.fixture
    def sample_tasks(self):
        """Create comprehensive sample tasks for testing."""
        # Create subtasks first
        subtask_1_1 = Task(
            id="1.1",
            description="Initialize project structure",
            requirements=["1.1"],
            status=TaskStatus.NOT_STARTED,
            level=1,
            parent_id="1",
            estimated_effort=2,
            details=[
                "Create frontend and backend directory structure",
                "Set up package.json and pyproject.toml configuration files",
                "Configure TypeScript and Python development environments"
            ]
        )
        
        subtask_1_2 = Task(
            id="1.2",
            description="Configure development tools",
            requirements=["1.1", "2.1"],
            status=TaskStatus.NOT_STARTED,
            level=1,
            parent_id="1",
            estimated_effort=3,
            details=[
                "Set up ESLint, Prettier, and TypeScript configuration",
                "Configure Python linting with Ruff and type checking with MyPy",
                "Set up pre-commit hooks for code quality enforcement"
            ]
        )
        
        # Create main tasks
        main_task_1 = Task(
            id="1",
            description="Set up project infrastructure and development environment",
            requirements=["1.1", "2.1", "3.1"],
            subtasks=[subtask_1_1, subtask_1_2],
            status=TaskStatus.NOT_STARTED,
            level=0,
            estimated_effort=5,
            details=[
                "Create project directory structure with proper organization",
                "Configure package management and dependency installation",
                "Set up development tools and code quality checks"
            ]
        )
        
        main_task_2 = Task(
            id="2",
            description="Implement core data models and database schema",
            requirements=["3.1", "3.2", "3.3"],
            dependencies=["1"],
            status=TaskStatus.NOT_STARTED,
            level=0,
            estimated_effort=8,
            details=[
                "Design and create database schema with proper relationships",
                "Implement SQLAlchemy models with validation and constraints",
                "Create database migration scripts and seed data"
            ]
        )
        
        main_task_3 = Task(
            id="3",
            description="Build authentication and authorization system",
            requirements=["1.1", "1.2", "1.3"],
            dependencies=["2"],
            status=TaskStatus.NOT_STARTED,
            level=0,
            estimated_effort=10,
            details=[
                "Implement JWT token generation and validation",
                "Create user registration and login endpoints",
                "Add role-based access control and permissions"
            ]
        )
        
        return [main_task_1, subtask_1_1, subtask_1_2, main_task_2, main_task_3]
    
    def test_load_execution_context_success(self, task_engine, mock_file_manager, mock_execution_context):
        """Test successful execution context loading with comprehensive mocking."""
        spec_id = "test-feature"
        
        # Mock file manager responses
        mock_file_manager.validate_spec_structure.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[]
        )
        
        # Create mock documents
        req_doc = SpecDocument(
            type=DocumentType.REQUIREMENTS,
            content=mock_execution_context.requirements_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="req_checksum"
            )
        )
        
        design_doc = SpecDocument(
            type=DocumentType.DESIGN,
            content=mock_execution_context.design_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="design_checksum"
            )
        )
        
        tasks_doc = SpecDocument(
            type=DocumentType.TASKS,
            content=mock_execution_context.tasks_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="tasks_checksum"
            )
        )
        
        mock_file_manager.load_document.side_effect = [
            (req_doc, Mock(success=True)),
            (design_doc, Mock(success=True)),
            (tasks_doc, Mock(success=True))
        ]
        
        mock_file_manager._load_spec_metadata.return_value = mock_execution_context.spec_metadata
        
        # Execute
        context, result = task_engine.load_execution_context(spec_id)
        
        # Verify
        assert result.is_valid
        assert context is not None
        assert context.requirements_content == mock_execution_context.requirements_content
        assert context.design_content == mock_execution_context.design_content
        assert context.tasks_content == mock_execution_context.tasks_content
        assert context.spec_metadata.id == spec_id
        
        # Verify file manager calls
        mock_file_manager.validate_spec_structure.assert_called_once_with(spec_id)
        assert mock_file_manager.load_document.call_count == 3
        mock_file_manager._load_spec_metadata.assert_called_once_with(spec_id)
    
    def test_load_execution_context_validation_failure(self, task_engine, mock_file_manager):
        """Test context loading with spec structure validation failure."""
        spec_id = "invalid-spec"
        
        # Mock validation failure
        mock_file_manager.validate_spec_structure.return_value = ValidationResult(
            is_valid=False,
            errors=[
                ValidationError(code="MISSING_REQUIREMENTS", message="Requirements file not found", field="requirements"),
                ValidationError(code="INVALID_STRUCTURE", message="Invalid spec directory structure", field="structure")
            ],
            warnings=[]
        )
        
        # Execute
        context, result = task_engine.load_execution_context(spec_id)
        
        # Verify
        assert not result.is_valid
        assert context is None
        assert len(result.errors) == 2
        assert any(error.code == "MISSING_REQUIREMENTS" for error in result.errors)
        assert any(error.code == "INVALID_STRUCTURE" for error in result.errors)
    
    def test_load_execution_context_document_loading_failure(self, task_engine, mock_file_manager):
        """Test context loading with document loading failure."""
        spec_id = "test-spec"
        
        # Mock successful validation but failed document loading
        mock_file_manager.validate_spec_structure.return_value = ValidationResult(
            is_valid=True, errors=[], warnings=[]
        )
        
        mock_file_manager.load_document.side_effect = [
            (None, Mock(success=False, message="Requirements file corrupted")),
            (Mock(), Mock(success=True)),
            (Mock(), Mock(success=True))
        ]
        
        # Execute
        context, result = task_engine.load_execution_context(spec_id)
        
        # Verify
        assert not result.is_valid
        assert context is None
        assert any("Requirements file corrupted" in error.message for error in result.errors)
    
    def test_parse_tasks_from_document_comprehensive(self, task_engine, mock_execution_context):
        """Test comprehensive task parsing from markdown document."""
        tasks = task_engine.parse_tasks_from_document(mock_execution_context.tasks_content)
        
        # Verify task count and structure
        assert len(tasks) >= 10  # Should parse all tasks and subtasks
        
        # Verify main tasks
        main_tasks = [task for task in tasks if task.level == 0]
        assert len(main_tasks) >= 5
        
        # Verify subtasks
        subtasks = [task for task in tasks if task.level == 1]
        assert len(subtasks) >= 5
        
        # Verify specific task parsing
        task_1 = next(task for task in tasks if task.id == "1")
        assert "infrastructure" in task_1.description.lower()
        assert "1.1" in task_1.requirements
        assert "2.1" in task_1.requirements
        assert "3.1" in task_1.requirements
        assert len(task_1.subtasks) >= 2
        
        # Verify subtask parsing
        subtask_1_1 = next(task for task in tasks if task.id == "1.1")
        assert subtask_1_1.parent_id == "1"
        assert subtask_1_1.level == 1
        assert "project structure" in subtask_1_1.description.lower()
        assert "1.1" in subtask_1_1.requirements
        
        # Verify requirement references are parsed
        all_requirements = []
        for task in tasks:
            all_requirements.extend(task.requirements)
        
        assert "1.1" in all_requirements
        assert "2.1" in all_requirements
        assert "3.1" in all_requirements
    
    def test_parse_tasks_with_various_status_indicators(self, task_engine):
        """Test parsing tasks with different status indicators."""
        tasks_content_with_status = """# Implementation Plan

- [x] 1. Completed main task
  - This task has been finished
  - _Requirements: 1.1_

- [x] 1.1 Completed subtask
  - Subtask is also done
  - _Requirements: 1.1_

- [-] 2. In progress task
  - Currently being worked on
  - _Requirements: 2.1_

- [ ] 3. Not started task
  - Waiting to be started
  - _Requirements: 3.1_

- [ ] 3.1 Not started subtask
  - Subtask not yet begun
  - _Requirements: 3.1_
"""
        
        tasks = task_engine.parse_tasks_from_document(tasks_content_with_status)
        
        # Verify status parsing
        task_statuses = {task.id: task.status for task in tasks}
        
        assert task_statuses["1"] == TaskStatus.COMPLETED
        assert task_statuses["1.1"] == TaskStatus.COMPLETED
        assert task_statuses["2"] == TaskStatus.IN_PROGRESS
        assert task_statuses["3"] == TaskStatus.NOT_STARTED
        assert task_statuses["3.1"] == TaskStatus.NOT_STARTED
    
    def test_update_task_status_success(self, task_engine, mock_file_manager, mock_execution_context):
        """Test successful task status update."""
        spec_id = "test-spec"
        task_id = "1"
        new_status = TaskStatus.IN_PROGRESS
        
        # Mock document loading
        tasks_doc = SpecDocument(
            type=DocumentType.TASKS,
            content=mock_execution_context.tasks_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="tasks_checksum"
            )
        )
        
        mock_file_manager.load_document.return_value = (tasks_doc, Mock(success=True))
        mock_file_manager.save_document.return_value = Mock(success=True)
        
        # Execute
        result = task_engine.update_task_status(spec_id, task_id, new_status)
        
        # Verify
        assert result.is_valid
        mock_file_manager.load_document.assert_called_once_with(spec_id, DocumentType.TASKS)
        mock_file_manager.save_document.assert_called_once()
        
        # Verify the saved content has updated status
        save_call_args = mock_file_manager.save_document.call_args
        saved_document = save_call_args[0][1]  # Second argument is the document
        assert "- [-] 1." in saved_document.content  # Should be marked as in progress
    
    def test_update_task_status_task_not_found(self, task_engine, mock_file_manager, mock_execution_context):
        """Test task status update with non-existent task."""
        spec_id = "test-spec"
        task_id = "999"  # Non-existent task
        new_status = TaskStatus.IN_PROGRESS
        
        # Mock document loading
        tasks_doc = SpecDocument(
            type=DocumentType.TASKS,
            content=mock_execution_context.tasks_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="tasks_checksum"
            )
        )
        
        mock_file_manager.load_document.return_value = (tasks_doc, Mock(success=True))
        
        # Execute
        result = task_engine.update_task_status(spec_id, task_id, new_status)
        
        # Verify
        assert not result.is_valid
        assert any(error.code == "TASK_NOT_FOUND" for error in result.errors)
        mock_file_manager.save_document.assert_not_called()
    
    def test_calculate_progress_comprehensive(self, task_engine, mock_file_manager, mock_execution_context, sample_tasks):
        """Test comprehensive progress calculation."""
        spec_id = "test-spec"
        
        # Set up task statuses for testing
        sample_tasks[0].status = TaskStatus.COMPLETED  # Main task 1
        sample_tasks[1].status = TaskStatus.COMPLETED  # Subtask 1.1
        sample_tasks[2].status = TaskStatus.COMPLETED  # Subtask 1.2
        sample_tasks[3].status = TaskStatus.IN_PROGRESS  # Main task 2
        sample_tasks[4].status = TaskStatus.NOT_STARTED  # Main task 3
        
        # Mock context loading
        mock_file_manager.validate_spec_structure.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
        mock_file_manager.load_document.return_value = (Mock(), Mock(success=True))
        mock_file_manager._load_spec_metadata.return_value = mock_execution_context.spec_metadata
        
        with patch.object(task_engine, 'load_execution_context', return_value=(mock_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))):
            with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
                progress, result = task_engine.calculate_progress(spec_id)
        
        # Verify
        assert result.is_valid
        assert progress['total_tasks'] == 5
        assert progress['completed_tasks'] == 3  # Main task 1 and its 2 subtasks
        assert progress['in_progress_tasks'] == 1  # Main task 2
        assert progress['not_started_tasks'] == 1  # Main task 3
        assert progress['completion_percentage'] == 60.0  # 3/5 * 100
        
        # Verify effort-based calculations
        assert 'total_effort' in progress
        assert 'completed_effort' in progress
        assert 'effort_completion_percentage' in progress
    
    def test_calculate_progress_no_tasks(self, task_engine, mock_file_manager, mock_execution_context):
        """Test progress calculation with no tasks."""
        spec_id = "empty-spec"
        
        # Mock context with empty tasks
        empty_context = ExecutionContext(
            requirements_content=mock_execution_context.requirements_content,
            design_content=mock_execution_context.design_content,
            tasks_content="# Implementation Plan\n\nNo tasks defined yet.",
            project_structure=mock_execution_context.project_structure,
            existing_code=mock_execution_context.existing_code,
            spec_metadata=mock_execution_context.spec_metadata
        )
        
        with patch.object(task_engine, 'load_execution_context', return_value=(empty_context, ValidationResult(is_valid=True, errors=[], warnings=[]))):
            with patch.object(task_engine, 'parse_tasks_from_document', return_value=[]):
                progress, result = task_engine.calculate_progress(spec_id)
        
        # Verify
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any(warning.code == "NO_TASKS_FOUND" for warning in result.warnings)
        assert progress['total_tasks'] == 0
        assert progress['completion_percentage'] == 0.0
    
    def test_execute_task_success_with_mocks(self, task_engine, mock_file_manager, mock_execution_context, sample_tasks):
        """Test successful task execution with comprehensive mocking."""
        spec_id = "test-spec"
        task_id = "1.1"  # Subtask
        
        # Mock all dependencies
        with patch.object(task_engine, 'validate_task_execution_readiness') as mock_validate_readiness:
            with patch.object(task_engine, 'load_execution_context') as mock_load_context:
                with patch.object(task_engine, 'parse_tasks_from_document') as mock_parse_tasks:
                    with patch.object(task_engine, 'update_task_status') as mock_update_status:
                        with patch.object(task_engine, '_execute_task_implementation') as mock_execute_impl:
                            with patch.object(task_engine, 'validate_task_completion') as mock_validate_completion:
                                
                                # Set up mocks
                                mock_validate_readiness.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
                                mock_load_context.return_value = (mock_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
                                mock_parse_tasks.return_value = sample_tasks
                                mock_update_status.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
                                
                                mock_execute_impl.return_value = TaskResult(
                                    task_id=task_id,
                                    success=True,
                                    message="Task completed successfully",
                                    files_created=["src/frontend/package.json", "src/backend/pyproject.toml"],
                                    files_modified=["README.md"],
                                    tests_run=["test_project_structure"],
                                    execution_time=2.5,
                                    details={
                                        "directories_created": ["src/frontend", "src/backend"],
                                        "configurations_set": ["typescript", "python", "linting"]
                                    }
                                )
                                
                                mock_validate_completion.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
                                
                                # Execute
                                result = task_engine.execute_task(spec_id, task_id)
        
        # Verify
        assert result.success
        assert result.task_id == task_id
        assert "src/frontend/package.json" in result.files_created
        assert "src/backend/pyproject.toml" in result.files_created
        assert "README.md" in result.files_modified
        assert result.execution_time == 2.5
        
        # Verify all steps were called
        mock_validate_readiness.assert_called_once_with(spec_id, task_id)
        mock_load_context.assert_called_once_with(spec_id)
        mock_parse_tasks.assert_called_once()
        mock_update_status.assert_called()  # Called twice: start and completion
        mock_execute_impl.assert_called_once()
        mock_validate_completion.assert_called_once()
    
    def test_execute_task_readiness_validation_failure(self, task_engine):
        """Test task execution when readiness validation fails."""
        spec_id = "test-spec"
        task_id = "1"
        
        with patch.object(task_engine, 'validate_task_execution_readiness') as mock_validate:
            mock_validate.return_value = ValidationResult(
                is_valid=False,
                errors=[
                    ValidationError(code="MISSING_DEPENDENCIES", message="Required dependencies not met", field="dependencies"),
                    ValidationError(code="INVALID_CONTEXT", message="Execution context is invalid", field="context")
                ],
                warnings=[]
            )
            
            # Execute
            result = task_engine.execute_task(spec_id, task_id)
        
        # Verify
        assert not result.success
        assert "not ready" in result.message.lower() or "dependencies" in result.message.lower()
        assert result.task_id == task_id
    
    def test_execute_task_with_recovery_multiple_attempts(self, task_engine):
        """Test task execution with recovery over multiple attempts."""
        spec_id = "test-spec"
        task_id = "2"
        max_retries = 3
        
        # Mock execute_task to fail first two times, succeed on third
        with patch.object(task_engine, 'execute_task') as mock_execute:
            with patch.object(task_engine, '_attempt_task_recovery') as mock_recovery:
                
                mock_execute.side_effect = [
                    TaskResult(task_id=task_id, success=False, message="First attempt failed: Permission denied"),
                    TaskResult(task_id=task_id, success=False, message="Second attempt failed: File not found"),
                    TaskResult(task_id=task_id, success=True, message="Third attempt succeeded")
                ]
                
                mock_recovery.side_effect = [
                    {'action': 'permission_fix', 'success': True, 'message': 'Fixed permissions'},
                    {'action': 'dependency_check', 'success': True, 'message': 'Created missing files'}
                ]
                
                # Execute
                result = task_engine.execute_task_with_recovery(spec_id, task_id, max_retries)
        
        # Verify
        assert result.success
        assert "after 2 recovery attempts" in result.message
        assert mock_execute.call_count == 3
        assert mock_recovery.call_count == 2
    
    def test_execute_task_with_recovery_max_retries_exceeded(self, task_engine):
        """Test task execution with recovery when max retries are exceeded."""
        spec_id = "test-spec"
        task_id = "3"
        max_retries = 2
        
        with patch.object(task_engine, 'execute_task') as mock_execute:
            with patch.object(task_engine, '_attempt_task_recovery') as mock_recovery:
                
                # All attempts fail
                mock_execute.return_value = TaskResult(
                    task_id=task_id, 
                    success=False, 
                    message="Persistent failure"
                )
                
                mock_recovery.return_value = {
                    'action': 'retry', 
                    'success': True, 
                    'message': 'Retrying'
                }
                
                # Execute
                result = task_engine.execute_task_with_recovery(spec_id, task_id, max_retries)
        
        # Verify
        assert not result.success
        assert "maximum retry attempts" in result.message.lower()
        assert mock_execute.call_count == max_retries + 1  # Initial + retries
    
    def test_attempt_task_recovery_strategies_comprehensive(self, task_engine):
        """Test comprehensive task recovery strategies."""
        spec_id = "test-spec"
        task_id = "1"
        
        recovery_test_cases = [
            {
                "failed_result": TaskResult(task_id=task_id, success=False, message="Permission denied accessing /etc/config"),
                "expected_action": "permission_fix",
                "expected_success": True
            },
            {
                "failed_result": TaskResult(task_id=task_id, success=False, message="File not found: requirements.txt"),
                "expected_action": "dependency_check",
                "expected_success": True
            },
            {
                "failed_result": TaskResult(task_id=task_id, success=False, message="Syntax error in generated code"),
                "expected_action": "code_fix",
                "expected_success": True
            },
            {
                "failed_result": TaskResult(task_id=task_id, success=False, message="Module 'unknown_module' not found"),
                "expected_action": "dependency_install",
                "expected_success": True
            },
            {
                "failed_result": TaskResult(task_id=task_id, success=False, message="Database connection timeout"),
                "expected_action": "service_restart",
                "expected_success": True
            },
            {
                "failed_result": TaskResult(task_id=task_id, success=False, message="Unknown mysterious error"),
                "expected_action": "cache_clear",
                "expected_success": True
            }
        ]
        
        for test_case in recovery_test_cases:
            recovery = task_engine._attempt_task_recovery(spec_id, task_id, test_case["failed_result"])
            
            assert recovery['action'] == test_case["expected_action"]
            assert recovery['success'] == test_case["expected_success"]
            assert isinstance(recovery['message'], str)
            assert len(recovery['message']) > 0
    
    def test_validate_task_execution_readiness_comprehensive(self, task_engine, mock_file_manager, mock_execution_context, sample_tasks):
        """Test comprehensive task execution readiness validation."""
        spec_id = "test-spec"
        
        readiness_test_cases = [
            {
                "task_id": "1",  # Main task with no dependencies
                "task_status": TaskStatus.NOT_STARTED,
                "dependencies_met": True,
                "should_be_ready": True
            },
            {
                "task_id": "2",  # Task with dependencies
                "task_status": TaskStatus.NOT_STARTED,
                "dependencies_met": False,  # Task 1 not completed
                "should_be_ready": False
            },
            {
                "task_id": "1.1",  # Subtask
                "task_status": TaskStatus.NOT_STARTED,
                "dependencies_met": True,
                "should_be_ready": True
            },
            {
                "task_id": "3",  # Task already completed
                "task_status": TaskStatus.COMPLETED,
                "dependencies_met": True,
                "should_be_ready": False  # Already completed
            }
        ]
        
        for test_case in readiness_test_cases:
            # Set up task statuses based on test case
            for task in sample_tasks:
                if task.id == test_case["task_id"]:
                    task.status = test_case["task_status"]
                elif task.id in ["1", "1.1", "1.2"] and not test_case["dependencies_met"]:
                    task.status = TaskStatus.NOT_STARTED  # Dependencies not met
                elif task.id in ["1", "1.1", "1.2"] and test_case["dependencies_met"]:
                    task.status = TaskStatus.COMPLETED  # Dependencies met
            
            with patch.object(task_engine, 'load_execution_context') as mock_load_context:
                with patch.object(task_engine, 'parse_tasks_from_document') as mock_parse_tasks:
                    
                    mock_load_context.return_value = (mock_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
                    mock_parse_tasks.return_value = sample_tasks
                    
                    # Execute
                    result = task_engine.validate_task_execution_readiness(spec_id, test_case["task_id"])
            
            # Verify
            if test_case["should_be_ready"]:
                assert result.is_valid, f"Task {test_case['task_id']} should be ready but validation failed"
            else:
                assert not result.is_valid, f"Task {test_case['task_id']} should not be ready but validation passed"
    
    def test_validate_task_completion_comprehensive(self, task_engine, mock_file_manager, mock_execution_context, sample_tasks):
        """Test comprehensive task completion validation."""
        spec_id = "test-spec"
        task_id = "1.1"
        
        # Create a comprehensive task result
        task_result = TaskResult(
            task_id=task_id,
            success=True,
            message="Task completed successfully",
            files_created=[
                "src/frontend/package.json",
                "src/backend/pyproject.toml",
                "src/frontend/tsconfig.json",
                "src/backend/requirements.txt"
            ],
            files_modified=[
                "README.md",
                ".gitignore",
                "docs/setup.md"
            ],
            tests_run=[
                "test_project_structure",
                "test_configuration_files",
                "test_development_environment"
            ],
            execution_time=3.2,
            details={
                "directories_created": ["src/frontend", "src/backend", "tests", "docs"],
                "configurations_set": ["typescript", "python", "eslint", "prettier"],
                "tools_installed": ["npm", "pip", "pre-commit"]
            }
        )
        
        with patch.object(task_engine, 'load_execution_context') as mock_load_context:
            with patch.object(task_engine, 'parse_tasks_from_document') as mock_parse_tasks:
                with patch.object(task_engine, '_validate_against_requirements') as mock_validate_reqs:
                    with patch.object(task_engine, '_validate_file_modifications') as mock_validate_files:
                        
                        mock_load_context.return_value = (mock_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
                        mock_parse_tasks.return_value = sample_tasks
                        mock_validate_reqs.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
                        mock_validate_files.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
                        
                        # Execute
                        result = task_engine.validate_task_completion(spec_id, task_id, task_result)
        
        # Verify
        assert result.is_valid
        mock_validate_reqs.assert_called_once()
        mock_validate_files.assert_called_once()
    
    def test_get_next_task_comprehensive(self, task_engine, mock_file_manager, mock_execution_context, sample_tasks):
        """Test comprehensive next task identification."""
        spec_id = "test-spec"
        
        # Test different scenarios
        next_task_scenarios = [
            {
                "name": "first_task_available",
                "task_statuses": {
                    "1": TaskStatus.NOT_STARTED,
                    "1.1": TaskStatus.NOT_STARTED,
                    "1.2": TaskStatus.NOT_STARTED,
                    "2": TaskStatus.NOT_STARTED,
                    "3": TaskStatus.NOT_STARTED
                },
                "expected_next": "1"  # First main task
            },
            {
                "name": "subtask_available",
                "task_statuses": {
                    "1": TaskStatus.IN_PROGRESS,
                    "1.1": TaskStatus.NOT_STARTED,
                    "1.2": TaskStatus.NOT_STARTED,
                    "2": TaskStatus.NOT_STARTED,
                    "3": TaskStatus.NOT_STARTED
                },
                "expected_next": "1.1"  # First subtask
            },
            {
                "name": "next_main_task",
                "task_statuses": {
                    "1": TaskStatus.COMPLETED,
                    "1.1": TaskStatus.COMPLETED,
                    "1.2": TaskStatus.COMPLETED,
                    "2": TaskStatus.NOT_STARTED,
                    "3": TaskStatus.NOT_STARTED
                },
                "expected_next": "2"  # Next main task
            },
            {
                "name": "all_tasks_completed",
                "task_statuses": {
                    "1": TaskStatus.COMPLETED,
                    "1.1": TaskStatus.COMPLETED,
                    "1.2": TaskStatus.COMPLETED,
                    "2": TaskStatus.COMPLETED,
                    "3": TaskStatus.COMPLETED
                },
                "expected_next": None  # No tasks available
            }
        ]
        
        for scenario in next_task_scenarios:
            # Set up task statuses
            for task in sample_tasks:
                if task.id in scenario["task_statuses"]:
                    task.status = scenario["task_statuses"][task.id]
            
            with patch.object(task_engine, 'load_execution_context') as mock_load_context:
                with patch.object(task_engine, 'parse_tasks_from_document') as mock_parse_tasks:
                    
                    mock_load_context.return_value = (mock_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
                    mock_parse_tasks.return_value = sample_tasks
                    
                    # Execute
                    next_task, result = task_engine.get_next_task(spec_id)
            
            # Verify
            assert result.is_valid
            
            if scenario["expected_next"] is None:
                assert next_task is None
                assert any(warning.code == "ALL_TASKS_COMPLETED" for warning in result.warnings)
            else:
                assert next_task is not None
                assert next_task.id == scenario["expected_next"]
    
    def test_get_execution_summary_comprehensive(self, task_engine, mock_file_manager, mock_execution_context, sample_tasks):
        """Test comprehensive execution summary generation."""
        spec_id = "test-spec"
        
        # Set up mixed task statuses
        sample_tasks[0].status = TaskStatus.COMPLETED  # Task 1
        sample_tasks[1].status = TaskStatus.COMPLETED  # Task 1.1
        sample_tasks[2].status = TaskStatus.COMPLETED  # Task 1.2
        sample_tasks[3].status = TaskStatus.IN_PROGRESS  # Task 2
        sample_tasks[4].status = TaskStatus.NOT_STARTED  # Task 3
        
        with patch.object(task_engine, 'calculate_progress') as mock_calc_progress:
            with patch.object(task_engine, 'load_execution_context') as mock_load_context:
                with patch.object(task_engine, 'parse_tasks_from_document') as mock_parse_tasks:
                    with patch.object(task_engine, 'get_next_task') as mock_get_next:
                        
                        mock_calc_progress.return_value = (
                            {
                                'total_tasks': 5,
                                'completed_tasks': 3,
                                'in_progress_tasks': 1,
                                'not_started_tasks': 1,
                                'completion_percentage': 60.0,
                                'total_effort': 28,
                                'completed_effort': 10,
                                'effort_completion_percentage': 35.7
                            },
                            ValidationResult(is_valid=True, errors=[], warnings=[])
                        )
                        
                        mock_load_context.return_value = (mock_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
                        mock_parse_tasks.return_value = sample_tasks
                        mock_get_next.return_value = (sample_tasks[3], ValidationResult(is_valid=True, errors=[], warnings=[]))
                        
                        # Execute
                        summary, result = task_engine.get_execution_summary(spec_id)
        
        # Verify comprehensive summary structure
        assert result.is_valid
        assert summary['spec_id'] == spec_id
        
        # Verify execution stats
        assert 'execution_stats' in summary
        stats = summary['execution_stats']
        assert stats['total_tasks'] == 5
        assert stats['completed_tasks'] == 3
        assert stats['in_progress_tasks'] == 1
        
        # Verify progress metrics
        assert 'progress_metrics' in summary
        metrics = summary['progress_metrics']
        assert metrics['completion_percentage'] == 60.0
        assert metrics['effort_completion_percentage'] == 35.7
        
        # Verify next actions
        assert 'next_actions' in summary
        actions = summary['next_actions']
        assert 'recommended_next_task' in actions
        assert actions['recommended_next_task']['id'] == "2"
        
        # Verify context info
        assert 'context_info' in summary
        context = summary['context_info']
        assert 'requirements_count' in context
        assert 'design_sections' in context
        assert 'technology_stack' in context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])