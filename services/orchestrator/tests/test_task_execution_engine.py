"""
Unit tests for the TaskExecutionEngine.

This module provides comprehensive testing for task execution logic,
context management, progress tracking, and error handling.

Requirements addressed:
- 4.13: Task execution testing and validation
- 6.9, 6.12: Task execution integration tests
"""

import pytest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from eco_api.specs.task_execution_engine import (
    TaskExecutionEngine, Task, ExecutionContext, TaskResult, ProjectStructure, CodeContext
)
from eco_api.specs.models import (
    TaskStatus, DocumentType, ValidationResult, ValidationError, ValidationWarning,
    SpecDocument, SpecMetadata, WorkflowPhase, WorkflowStatus, DocumentMetadata
)
from eco_api.specs.file_manager import FileSystemManager


# Test fixtures at module level
@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def task_engine(temp_workspace):
    """Create a TaskExecutionEngine instance for testing."""
    return TaskExecutionEngine(temp_workspace)

@pytest.fixture
def sample_spec_metadata():
    """Create sample spec metadata for testing."""
    return SpecMetadata(
        id="test-feature",
        feature_name="test-feature",
        version="1.0.0",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        current_phase=WorkflowPhase.EXECUTION,
        status=WorkflowStatus.IN_PROGRESS,
        checksum={}
    )

@pytest.fixture
def sample_execution_context(sample_spec_metadata):
    """Create sample execution context for testing."""
    return ExecutionContext(
        requirements_content="# Requirements\n\n## Requirement 1\n\n**User Story:** As a user...",
        design_content="# Design\n\n## Overview\n\nThis is the design...",
        tasks_content="""# Implementation Plan

- [ ] 1. First task
  - Create initial structure
  - _Requirements: 1.1_

- [ ] 1.1 First subtask
  - Implement basic functionality
  - _Requirements: 1.1_

- [ ] 2. Second task
  - Add advanced features
  - _Requirements: 1.2_
""",
        project_structure=ProjectStructure(
            root_path="/test/workspace",
            directories=["src", "tests"],
            files=["src/main.py", "tests/test_main.py"],
            package_files=["package.json"]
        ),
        existing_code=CodeContext(
            existing_files={"src/main.py": "# Main file"},
            imports=["import os"],
            classes=["MainClass"],
            functions=["main_function"]
        ),
        spec_metadata=sample_spec_metadata
    )

@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing."""
    subtask = Task(
        id="1.1",
        description="First subtask",
        requirements=["1.1"],
        status=TaskStatus.NOT_STARTED,
        level=1
    )
    
    parent_task = Task(
        id="1",
        description="First task",
        requirements=["1.1"],
        subtasks=[subtask],
        status=TaskStatus.NOT_STARTED,
        level=0
    )
    
    subtask.parent_id = parent_task.id
    
    second_task = Task(
        id="2",
        description="Second task",
        requirements=["1.2"],
        dependencies=["1"],
        status=TaskStatus.NOT_STARTED,
        level=0
    )
    
    return [parent_task, subtask, second_task]


class TestTaskExecutionEngine:
    """Test suite for TaskExecutionEngine."""


class TestTaskParsing:
    """Test task parsing functionality."""
    
    def test_parse_tasks_from_document(self, task_engine, sample_execution_context):
        """Test parsing tasks from markdown document."""
        tasks = task_engine.parse_tasks_from_document(sample_execution_context.tasks_content)
        
        assert len(tasks) == 3
        
        # Check parent task
        parent_task = next(t for t in tasks if t.id == "1")
        assert parent_task.description == "First task"
        assert parent_task.level == 0
        assert len(parent_task.subtasks) == 1
        assert "1.1" in parent_task.requirements
        
        # Check subtask
        subtask = next(t for t in tasks if t.id == "1.1")
        assert subtask.description == "First subtask"
        assert subtask.level == 1
        assert subtask.parent_id == "1"
        assert "1.1" in subtask.requirements
        
        # Check second task
        second_task = next(t for t in tasks if t.id == "2")
        assert second_task.description == "Second task"
        assert second_task.level == 0
        assert "1.2" in second_task.requirements
    
    def test_parse_tasks_with_status(self, task_engine):
        """Test parsing tasks with different status indicators."""
        tasks_content = """# Tasks

- [x] 1. Completed task
- [-] 2. In progress task  
- [ ] 3. Not started task
- [!] 4. Blocked task
"""
        
        tasks = task_engine.parse_tasks_from_document(tasks_content)
        
        assert len(tasks) == 4
        assert tasks[0].status == TaskStatus.COMPLETED
        assert tasks[1].status == TaskStatus.IN_PROGRESS
        assert tasks[2].status == TaskStatus.NOT_STARTED
        # Note: Blocked status would need to be handled in parsing logic
    
    def test_parse_empty_tasks_document(self, task_engine):
        """Test parsing empty tasks document."""
        tasks = task_engine.parse_tasks_from_document("")
        assert len(tasks) == 0
        
        tasks = task_engine.parse_tasks_from_document("# Tasks\n\nNo tasks defined.")
        assert len(tasks) == 0


class TestContextManagement:
    """Test execution context management."""
    
    @patch.object(FileSystemManager, 'validate_spec_structure')
    @patch.object(FileSystemManager, 'load_document')
    @patch.object(FileSystemManager, '_load_spec_metadata')
    def test_load_execution_context_success(self, mock_load_metadata, mock_load_doc, mock_validate, 
                                          task_engine, sample_spec_metadata, sample_execution_context):
        """Test successful execution context loading."""
        # Mock file manager responses
        mock_validate.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        req_doc = SpecDocument(
            type=DocumentType.REQUIREMENTS,
            content=sample_execution_context.requirements_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="abc123"
            )
        )
        
        design_doc = SpecDocument(
            type=DocumentType.DESIGN,
            content=sample_execution_context.design_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="def456"
            )
        )
        
        tasks_doc = SpecDocument(
            type=DocumentType.TASKS,
            content=sample_execution_context.tasks_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="ghi789"
            )
        )
        
        mock_load_doc.side_effect = [
            (req_doc, Mock(success=True)),
            (design_doc, Mock(success=True)),
            (tasks_doc, Mock(success=True))
        ]
        
        mock_load_metadata.return_value = sample_spec_metadata
        
        # Test context loading
        context, result = task_engine.load_execution_context("test-feature")
        
        assert result.is_valid
        assert context is not None
        assert context.requirements_content == sample_execution_context.requirements_content
        assert context.design_content == sample_execution_context.design_content
        assert context.tasks_content == sample_execution_context.tasks_content
    
    @patch.object(FileSystemManager, 'validate_spec_structure')
    def test_load_execution_context_invalid_structure(self, mock_validate, task_engine):
        """Test context loading with invalid spec structure."""
        mock_validate.return_value = ValidationResult(
            is_valid=False,
            errors=[ValidationError(code="INVALID_STRUCTURE", message="Invalid spec structure", field="structure")],
            warnings=[]
        )
        
        context, result = task_engine.load_execution_context("test-feature")
        
        assert not result.is_valid
        assert context is None
        assert len(result.errors) == 1
        assert result.errors[0].code == "INVALID_STRUCTURE"
    
    def test_execution_context_validation(self, sample_execution_context):
        """Test execution context validation."""
        # Valid context
        result = sample_execution_context.validate()
        assert result.is_valid
        
        # Invalid context - missing requirements
        invalid_context = ExecutionContext(
            requirements_content="",
            design_content=sample_execution_context.design_content,
            tasks_content=sample_execution_context.tasks_content,
            project_structure=sample_execution_context.project_structure,
            existing_code=sample_execution_context.existing_code,
            spec_metadata=sample_execution_context.spec_metadata
        )
        
        result = invalid_context.validate()
        assert not result.is_valid
        assert any(error.code == "MISSING_REQUIREMENTS" for error in result.errors)


class TestTaskStatusTracking:
    """Test task status tracking and updates."""
    
    @patch.object(FileSystemManager, 'load_document')
    @patch.object(FileSystemManager, 'save_document')
    def test_update_task_status_success(self, mock_save, mock_load, task_engine, sample_execution_context):
        """Test successful task status update."""
        # Mock document loading
        tasks_doc = SpecDocument(
            type=DocumentType.TASKS,
            content=sample_execution_context.tasks_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="abc123"
            )
        )
        
        mock_load.return_value = (tasks_doc, Mock(success=True))
        mock_save.return_value = Mock(success=True)
        
        # Test status update
        result = task_engine.update_task_status("test-feature", "1", TaskStatus.IN_PROGRESS)
        
        assert result.is_valid
        mock_save.assert_called_once()
    
    @patch.object(FileSystemManager, 'load_document')
    def test_update_task_status_task_not_found(self, mock_load, task_engine, sample_execution_context):
        """Test task status update with non-existent task."""
        tasks_doc = SpecDocument(
            type=DocumentType.TASKS,
            content=sample_execution_context.tasks_content,
            metadata=DocumentMetadata(
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                version="1.0.0",
                checksum="abc123"
            )
        )
        
        mock_load.return_value = (tasks_doc, Mock(success=True))
        
        result = task_engine.update_task_status("test-feature", "999", TaskStatus.IN_PROGRESS)
        
        assert not result.is_valid
        assert any(error.code == "TASK_NOT_FOUND" for error in result.errors)
    
    def test_validate_status_transition(self, task_engine):
        """Test status transition validation."""
        # Valid transitions
        assert task_engine._validate_status_transition(TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS)
        assert task_engine._validate_status_transition(TaskStatus.IN_PROGRESS, TaskStatus.COMPLETED)
        assert task_engine._validate_status_transition(TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS)
        
        # Invalid transitions (if any restrictions exist)
        # This would depend on the specific business rules implemented
    
    def test_update_task_status_in_content(self, task_engine):
        """Test updating task status in markdown content."""
        content = """# Tasks

- [ ] 1. First task
- [-] 2. Second task
- [x] 3. Third task
"""
        
        updated_content = task_engine._update_task_status_in_content(content, "1", TaskStatus.IN_PROGRESS)
        
        assert "- [-] 1. First task" in updated_content
        assert "- [-] 2. Second task" in updated_content  # Unchanged
        assert "- [x] 3. Third task" in updated_content   # Unchanged


class TestProgressCalculation:
    """Test progress calculation and reporting."""
    
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    def test_calculate_progress_success(self, mock_load_context, task_engine, sample_execution_context, sample_tasks):
        """Test successful progress calculation."""
        # Set up task statuses
        sample_tasks[0].status = TaskStatus.COMPLETED  # Parent task
        sample_tasks[1].status = TaskStatus.COMPLETED  # Subtask
        sample_tasks[2].status = TaskStatus.NOT_STARTED  # Second task
        
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        
        # Mock parse_tasks_from_document to return our sample tasks
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
            progress, result = task_engine.calculate_progress("test-feature")
        
        assert result.is_valid
        assert progress['total_tasks'] == 3
        assert progress['completed_tasks'] == 2
        assert progress['not_started_tasks'] == 1
        assert progress['completion_percentage'] > 0
    
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    def test_calculate_progress_no_tasks(self, mock_load_context, task_engine, sample_execution_context):
        """Test progress calculation with no tasks."""
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=[]):
            progress, result = task_engine.calculate_progress("test-feature")
        
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any(warning.code == "NO_TASKS_FOUND" for warning in result.warnings)
    
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    @patch.object(TaskExecutionEngine, 'calculate_progress')
    def test_get_task_progress_report(self, mock_calc_progress, mock_load_context, task_engine, sample_execution_context, sample_tasks):
        """Test generating task progress report."""
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        mock_calc_progress.return_value = (
            {'total_tasks': 3, 'completed_tasks': 1},
            ValidationResult(is_valid=True, errors=[], warnings=[])
        )
        
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
            report, result = task_engine.get_task_progress_report("test-feature", "1")
        
        assert result.is_valid
        assert 'spec_id' in report
        assert 'overall_progress' in report
        assert 'task_details' in report
        assert report['task_details']['id'] == "1"


class TestTaskExecution:
    """Test task execution functionality."""
    
    @patch.object(TaskExecutionEngine, 'validate_task_execution_readiness')
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    @patch.object(TaskExecutionEngine, 'update_task_status')
    @patch.object(TaskExecutionEngine, '_execute_task_implementation')
    @patch.object(TaskExecutionEngine, 'validate_task_completion')
    def test_execute_task_success(self, mock_validate_completion, mock_execute_impl, mock_update_status,
                                 mock_load_context, mock_validate_readiness, task_engine, 
                                 sample_execution_context, sample_tasks):
        """Test successful task execution."""
        # Mock all dependencies
        mock_validate_readiness.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        mock_update_status.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        mock_execute_impl.return_value = TaskResult(
            task_id="1",
            success=True,
            message="Task completed successfully",
            files_created=["test_file.py"],
            files_modified=[],
            tests_run=[]
        )
        
        mock_validate_completion.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
            result = task_engine.execute_task("test-feature", "1")
        
        assert result.success
        assert result.task_id == "1"
        assert "test_file.py" in result.files_created
    
    @patch.object(TaskExecutionEngine, 'validate_task_execution_readiness')
    def test_execute_task_not_ready(self, mock_validate_readiness, task_engine):
        """Test task execution when task is not ready."""
        mock_validate_readiness.return_value = ValidationResult(
            is_valid=False,
            errors=[ValidationError(code="NOT_READY", message="Task not ready", field="readiness")],
            warnings=[]
        )
        
        result = task_engine.execute_task("test-feature", "1")
        
        assert not result.success
        assert "not ready" in result.message.lower()
    
    def test_execute_task_implementation_simulation(self, task_engine, sample_tasks):
        """Test the simulated task implementation."""
        task = sample_tasks[0]  # First task
        context = Mock()
        
        result = task_engine._execute_task_implementation(task, context)
        
        assert result.success
        assert result.task_id == task.id
        # Should simulate file operations based on task description
    
    @patch.object(TaskExecutionEngine, 'execute_task')
    def test_execute_task_with_recovery_success_first_attempt(self, mock_execute, task_engine):
        """Test task execution with recovery - success on first attempt."""
        mock_execute.return_value = TaskResult(
            task_id="1",
            success=True,
            message="Task completed successfully"
        )
        
        result = task_engine.execute_task_with_recovery("test-feature", "1", max_retries=3)
        
        assert result.success
        assert mock_execute.call_count == 1
    
    @patch.object(TaskExecutionEngine, 'execute_task')
    @patch.object(TaskExecutionEngine, '_attempt_task_recovery')
    def test_execute_task_with_recovery_success_after_retry(self, mock_recovery, mock_execute, task_engine):
        """Test task execution with recovery - success after retry."""
        # First attempt fails, second succeeds
        mock_execute.side_effect = [
            TaskResult(task_id="1", success=False, message="First attempt failed"),
            TaskResult(task_id="1", success=True, message="Second attempt succeeded")
        ]
        
        mock_recovery.return_value = {'action': 'retry', 'success': True, 'message': 'Retrying'}
        
        result = task_engine.execute_task_with_recovery("test-feature", "1", max_retries=3)
        
        assert result.success
        assert "after 1 recovery attempts" in result.message
        assert mock_execute.call_count == 2
    
    def test_attempt_task_recovery_strategies(self, task_engine):
        """Test different task recovery strategies."""
        # Permission error
        failed_result = TaskResult(task_id="1", success=False, message="Permission denied")
        recovery = task_engine._attempt_task_recovery("test-feature", "1", failed_result)
        assert recovery['action'] == 'permission_fix'
        
        # Missing dependency
        failed_result = TaskResult(task_id="1", success=False, message="File not found")
        recovery = task_engine._attempt_task_recovery("test-feature", "1", failed_result)
        assert recovery['action'] == 'dependency_check'
        
        # Syntax error
        failed_result = TaskResult(task_id="1", success=False, message="Syntax error in code")
        recovery = task_engine._attempt_task_recovery("test-feature", "1", failed_result)
        assert recovery['action'] == 'code_fix'
        
        # Generic error
        failed_result = TaskResult(task_id="1", success=False, message="Unknown error")
        recovery = task_engine._attempt_task_recovery("test-feature", "1", failed_result)
        assert recovery['action'] == 'cache_clear'


class TestTaskValidation:
    """Test task validation functionality."""
    
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    def test_validate_task_execution_readiness_success(self, mock_load_context, task_engine, 
                                                      sample_execution_context, sample_tasks):
        """Test successful task execution readiness validation."""
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
            result = task_engine.validate_task_execution_readiness("test-feature", "1")
        
        assert result.is_valid
    
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    def test_validate_task_execution_readiness_task_not_found(self, mock_load_context, task_engine, 
                                                             sample_execution_context, sample_tasks):
        """Test task readiness validation with non-existent task."""
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
            result = task_engine.validate_task_execution_readiness("test-feature", "999")
        
        assert not result.is_valid
        assert any(error.code == "TASK_NOT_FOUND" for error in result.errors)
    
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    def test_validate_task_completion_success(self, mock_load_context, task_engine, 
                                            sample_execution_context, sample_tasks):
        """Test successful task completion validation."""
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        
        task_result = TaskResult(
            task_id="1",
            success=True,
            message="Task completed",
            files_created=["new_file.py"],
            files_modified=["existing_file.py"],
            tests_run=["test_suite"]
        )
        
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
            with patch.object(task_engine, '_validate_against_requirements', 
                            return_value=ValidationResult(is_valid=True, errors=[], warnings=[])):
                with patch.object(task_engine, '_validate_file_modifications',
                                return_value=ValidationResult(is_valid=True, errors=[], warnings=[])):
                    result = task_engine.validate_task_completion("test-feature", "1", task_result)
        
        assert result.is_valid
    
    def test_validate_against_requirements(self, task_engine, sample_tasks):
        """Test validation against requirements."""
        task = sample_tasks[0]
        task_result = TaskResult(
            task_id="1",
            success=True,
            message="Task completed",
            files_created=["new_file.py"]
        )
        requirements_content = "Requirements: 1.1 - User authentication"
        
        result = task_engine._validate_against_requirements(task, task_result, requirements_content)
        
        # Should have warnings about requirement not found (since our mock requirement doesn't match)
        assert result.is_valid  # No errors, just warnings
        assert len(result.warnings) > 0


class TestNextTaskIdentification:
    """Test next task identification functionality."""
    
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    def test_get_next_task_success(self, mock_load_context, task_engine, 
                                  sample_execution_context, sample_tasks):
        """Test successful next task identification."""
        # Set up task statuses - first task completed, second ready
        sample_tasks[0].status = TaskStatus.COMPLETED
        sample_tasks[1].status = TaskStatus.COMPLETED
        sample_tasks[2].status = TaskStatus.NOT_STARTED
        
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
            next_task, result = task_engine.get_next_task("test-feature")
        
        assert result.is_valid
        assert next_task is not None
        assert next_task.id == "2"  # Second task should be next
    
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    def test_get_next_task_no_available_tasks(self, mock_load_context, task_engine, 
                                            sample_execution_context, sample_tasks):
        """Test next task identification when no tasks are available."""
        # Set all tasks to completed
        for task in sample_tasks:
            task.status = TaskStatus.COMPLETED
        
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
            next_task, result = task_engine.get_next_task("test-feature")
        
        assert result.is_valid
        assert next_task is None
        assert any(warning.code == "ALL_TASKS_COMPLETED" for warning in result.warnings)


class TestExecutionSummary:
    """Test execution summary functionality."""
    
    @patch.object(TaskExecutionEngine, 'calculate_progress')
    @patch.object(TaskExecutionEngine, 'load_execution_context')
    @patch.object(TaskExecutionEngine, 'get_next_task')
    def test_get_execution_summary_success(self, mock_get_next, mock_load_context, mock_calc_progress,
                                         task_engine, sample_execution_context, sample_tasks):
        """Test successful execution summary generation."""
        mock_calc_progress.return_value = (
            {'total_tasks': 3, 'completed_tasks': 1, 'in_progress_tasks': 1},
            ValidationResult(is_valid=True, errors=[], warnings=[])
        )
        
        mock_load_context.return_value = (sample_execution_context, ValidationResult(is_valid=True, errors=[], warnings=[]))
        
        mock_get_next.return_value = (sample_tasks[2], ValidationResult(is_valid=True, errors=[], warnings=[]))
        
        with patch.object(task_engine, 'parse_tasks_from_document', return_value=sample_tasks):
            summary, result = task_engine.get_execution_summary("test-feature")
        
        assert result.is_valid
        assert 'spec_id' in summary
        assert 'execution_stats' in summary
        assert 'progress_metrics' in summary
        assert 'next_actions' in summary
        assert 'context_info' in summary
        assert summary['spec_id'] == "test-feature"
    
    def test_identify_critical_path(self, task_engine, sample_tasks):
        """Test critical path identification."""
        critical_path = task_engine._identify_critical_path(sample_tasks)
        
        # Should identify tasks in dependency order
        assert len(critical_path) > 0
        # First task should be in critical path since it has no dependencies
        assert any(task['id'] == '1' for task in critical_path)
    
    def test_identify_bottlenecks(self, task_engine, sample_tasks):
        """Test bottleneck identification."""
        # Set up a scenario where task 1 is blocking task 2
        sample_tasks[0].status = TaskStatus.IN_PROGRESS  # Task 1 in progress
        sample_tasks[2].status = TaskStatus.NOT_STARTED  # Task 2 waiting
        
        bottlenecks = task_engine._identify_bottlenecks(sample_tasks)
        
        # Task 1 should be identified as a bottleneck since it's blocking task 2
        assert any(bottleneck['id'] == '1' for bottleneck in bottlenecks)


# Integration test fixtures and helpers
@pytest.fixture
def mock_file_system_manager():
    """Create a mock FileSystemManager for integration tests."""
    manager = Mock(spec=FileSystemManager)
    
    # Set up default return values
    manager.validate_spec_structure.return_value = ValidationResult(is_valid=True, errors=[], warnings=[])
    manager.load_document.return_value = (Mock(), Mock(success=True))
    manager.save_document.return_value = Mock(success=True)
    manager._load_spec_metadata.return_value = Mock()
    
    return manager


class TestTaskExecutionEngineIntegration:
    """Integration tests for TaskExecutionEngine."""
    
    def test_full_task_execution_workflow(self, temp_workspace):
        """Test complete task execution workflow integration."""
        # This would be a more comprehensive integration test
        # that sets up a real file system with spec documents
        # and tests the entire workflow from context loading to task completion
        
        # Create a real TaskExecutionEngine
        engine = TaskExecutionEngine(temp_workspace)
        
        # Set up test spec files
        spec_dir = Path(temp_workspace) / ".kiro" / "specs" / "test-feature"
        spec_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test tasks document
        tasks_content = """# Implementation Plan

- [ ] 1. Create basic structure
  - Set up project files
  - _Requirements: 1.1_

- [ ] 1.1 Initialize project
  - Create main files
  - _Requirements: 1.1_
"""
        
        (spec_dir / "tasks.md").write_text(tasks_content)
        (spec_dir / "requirements.md").write_text("# Requirements\n\n## Requirement 1.1\n\nBasic setup")
        (spec_dir / "design.md").write_text("# Design\n\n## Overview\n\nBasic design")
        
        # Create metadata
        metadata = {
            "id": "test-feature",
            "feature_name": "test-feature",
            "version": "1.0.0",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "current_phase": "execution",
            "status": "in_progress",
            "checksum": {}
        }
        
        import json
        (spec_dir / ".spec-metadata.json").write_text(json.dumps(metadata, indent=2))
        
        # Test context loading
        context, result = engine.load_execution_context("test-feature")
        
        # Should succeed with real files
        assert result.is_valid
        assert context is not None
        assert "Create basic structure" in context.tasks_content
    
    @pytest.mark.parametrize("task_description,expected_files", [
        ("Create new module", ["simulated_file_1.py"]),
        ("Implement user authentication", ["existing_file_1.py"]),
        ("Write unit tests for login", ["test_1"]),
    ])
    def test_task_implementation_simulation_variations(self, task_engine, task_description, expected_files):
        """Test task implementation simulation with various task types."""
        task = Task(
            id="1",
            description=task_description,
            requirements=["1.1"],
            status=TaskStatus.NOT_STARTED
        )
        
        context = Mock()
        result = task_engine._execute_task_implementation(task, context)
        
        assert result.success
        # Check that appropriate files are simulated based on task description
        all_files = result.files_created + result.files_modified + result.tests_run
        assert len(all_files) > 0


if __name__ == "__main__":
    pytest.main([__file__])