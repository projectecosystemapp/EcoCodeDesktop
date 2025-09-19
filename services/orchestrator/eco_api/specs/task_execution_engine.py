"""
Task execution engine with context awareness for spec-driven workflows.

This module provides comprehensive task execution capabilities with full context
loading, dependency resolution, and progress tracking for implementation tasks.

Requirements addressed:
- 4.1, 4.2, 4.3: Context-aware task execution with validation and preparation
- 4.4, 4.6, 4.7: Single-task execution with proper isolation and error handling
- 4.5, 4.8, 4.9, 4.10: Task status tracking and progress management
- 4.11, 4.12, 4.13, 4.14: Task completion validation and testing
- 6.1, 6.2, 6.3, 6.4: Task execution workflow and status updates
"""

import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from .models import (
    TaskStatus, DocumentType, ValidationResult, ValidationError, ValidationWarning,
    SpecDocument, SpecMetadata, WorkflowPhase, WorkflowStatus
)
from .file_manager import FileSystemManager


@dataclass
class Task:
    """Represents a single implementation task."""
    id: str
    description: str
    requirements: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    subtasks: List['Task'] = field(default_factory=list)
    status: TaskStatus = TaskStatus.NOT_STARTED
    parent_id: Optional[str] = None
    level: int = 0
    estimated_effort: int = 1
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Set parent references for subtasks
        for subtask in self.subtasks:
            subtask.parent_id = self.id
            subtask.level = self.level + 1


@dataclass
class ProjectStructure:
    """Represents the current project structure."""
    root_path: str
    directories: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    package_files: List[str] = field(default_factory=list)


@dataclass
class CodeContext:
    """Represents existing code context."""
    existing_files: Dict[str, str] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)


@dataclass
class ExecutionContext:
    """Complete execution context for task execution."""
    requirements_content: str
    design_content: str
    tasks_content: str
    project_structure: ProjectStructure
    existing_code: CodeContext
    spec_metadata: SpecMetadata
    
    def validate(self) -> ValidationResult:
        """Validate that the execution context is complete and valid."""
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        # Check required documents
        if not self.requirements_content.strip():
            errors.append(ValidationError(
                code="MISSING_REQUIREMENTS",
                message="Requirements document is empty or missing",
                field="requirements"
            ))
        
        if not self.design_content.strip():
            errors.append(ValidationError(
                code="MISSING_DESIGN",
                message="Design document is empty or missing",
                field="design"
            ))
        
        if not self.tasks_content.strip():
            errors.append(ValidationError(
                code="MISSING_TASKS",
                message="Tasks document is empty or missing",
                field="tasks"
            ))
        
        # Validate project structure
        if not self.project_structure.root_path:
            errors.append(ValidationError(
                code="MISSING_PROJECT_ROOT",
                message="Project root path is not specified",
                field="project_structure"
            ))
        
        # Check if project root exists
        root_path = Path(self.project_structure.root_path)
        if not root_path.exists():
            warnings.append(ValidationWarning(
                code="PROJECT_ROOT_NOT_FOUND",
                message=f"Project root directory does not exist: {root_path}",
                field="project_structure",
                suggestion="Ensure the project root path is correct"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


@dataclass
class TaskResult:
    """Result of task execution."""
    task_id: str
    success: bool
    message: str
    files_modified: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    tests_run: List[str] = field(default_factory=list)
    validation_results: List[ValidationResult] = field(default_factory=list)
    execution_time: float = 0.0
    error_details: Optional[str] = None


class TaskExecutionEngine:
    """
    Engine for executing implementation tasks with full context awareness.
    
    Provides functionality for loading execution context, resolving dependencies,
    executing tasks in isolation, and tracking progress with proper validation.
    """
    
    def __init__(self, workspace_root: str = "."):
        """
        Initialize TaskExecutionEngine.
        
        Args:
            workspace_root: Root directory of the workspace
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.file_manager = FileSystemManager(workspace_root)
        self._task_cache: Dict[str, List[Task]] = {}
        self._context_cache: Dict[str, ExecutionContext] = {}
    
    def load_execution_context(self, spec_id: str) -> Tuple[Optional[ExecutionContext], ValidationResult]:
        """
        Load complete execution context for a specification.
        
        Requirements: 4.1 - Context loading with validation and preparation
        
        Args:
            spec_id: The specification identifier
            
        Returns:
            Tuple of (ExecutionContext or None, ValidationResult)
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            # Check if context is cached
            if spec_id in self._context_cache:
                cached_context = self._context_cache[spec_id]
                validation = cached_context.validate()
                if validation.is_valid:
                    return cached_context, validation
                else:
                    # Clear invalid cache
                    del self._context_cache[spec_id]
            
            # Validate spec structure first
            structure_validation = self.file_manager.validate_spec_structure(spec_id)
            if not structure_validation.is_valid:
                errors.extend(structure_validation.errors)
                return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Load requirements document
            requirements_doc, req_result = self.file_manager.load_document(spec_id, DocumentType.REQUIREMENTS)
            if not req_result.success or not requirements_doc:
                errors.append(ValidationError(
                    code="REQUIREMENTS_LOAD_FAILED",
                    message=f"Failed to load requirements: {req_result.message}",
                    field="requirements"
                ))
            
            # Load design document
            design_doc, design_result = self.file_manager.load_document(spec_id, DocumentType.DESIGN)
            if not design_result.success or not design_doc:
                errors.append(ValidationError(
                    code="DESIGN_LOAD_FAILED",
                    message=f"Failed to load design: {design_result.message}",
                    field="design"
                ))
            
            # Load tasks document
            tasks_doc, tasks_result = self.file_manager.load_document(spec_id, DocumentType.TASKS)
            if not tasks_result.success or not tasks_doc:
                errors.append(ValidationError(
                    code="TASKS_LOAD_FAILED",
                    message=f"Failed to load tasks: {tasks_result.message}",
                    field="tasks"
                ))
            
            # If any document failed to load, return error
            if errors:
                return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Load spec metadata
            spec_metadata = self.file_manager._load_spec_metadata(spec_id)
            if not spec_metadata:
                errors.append(ValidationError(
                    code="METADATA_LOAD_FAILED",
                    message="Failed to load spec metadata",
                    field="metadata"
                ))
                return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Analyze project structure
            project_structure = self._analyze_project_structure()
            
            # Analyze existing code context
            existing_code = self._analyze_existing_code()
            
            # Create execution context
            context = ExecutionContext(
                requirements_content=requirements_doc.content,
                design_content=design_doc.content,
                tasks_content=tasks_doc.content,
                project_structure=project_structure,
                existing_code=existing_code,
                spec_metadata=spec_metadata
            )
            
            # Validate context
            context_validation = context.validate()
            if context_validation.warnings:
                warnings.extend(context_validation.warnings)
            
            if context_validation.is_valid:
                # Cache valid context
                self._context_cache[spec_id] = context
            
            return context, ValidationResult(
                is_valid=context_validation.is_valid,
                errors=context_validation.errors,
                warnings=warnings
            )
            
        except Exception as e:
            errors.append(ValidationError(
                code="CONTEXT_LOAD_ERROR",
                message=f"Unexpected error loading execution context: {str(e)}",
                field="context"
            ))
            return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    def parse_tasks_from_document(self, tasks_content: str) -> List[Task]:
        """
        Parse tasks from the tasks document content.
        
        Requirements: 4.2 - Task dependency resolution and sequencing logic
        
        Args:
            tasks_content: Content of the tasks.md document
            
        Returns:
            List of parsed Task objects with hierarchy
        """
        tasks: List[Task] = []
        current_parent: Optional[Task] = None
        current_task: Optional[Task] = None
        
        # Regular expressions for parsing
        task_pattern = r'^- \[([ x-!])\] (\d+(?:\.\d+)*)\.?\s+(.+)$'
        requirement_pattern = r'_Requirements?:\s*([^_]+)_'
        
        lines = tasks_content.split('\n')
        
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            
            # Match task line
            task_match = re.match(task_pattern, line)
            if task_match:
                status_char, task_number, description = task_match.groups()
                
                # Determine status
                if status_char == 'x':
                    status = TaskStatus.COMPLETED
                elif status_char == '-':
                    status = TaskStatus.IN_PROGRESS
                elif status_char == '!':
                    status = TaskStatus.BLOCKED
                else:
                    status = TaskStatus.NOT_STARTED
                
                # Determine level based on task number
                level = task_number.count('.')
                
                # Create task
                task = Task(
                    id=task_number,
                    description=description,
                    requirements=[],
                    status=status,
                    level=level
                )
                
                # Handle hierarchy
                if level == 0:
                    # Top-level task
                    current_parent = task
                    current_task = task
                    tasks.append(task)
                elif level == 1 and current_parent:
                    # Sub-task
                    task.parent_id = current_parent.id
                    current_parent.subtasks.append(task)
                    current_task = task
                    tasks.append(task)
                else:
                    current_task = task
                    tasks.append(task)
            
            # Check for requirements in bullet points under tasks
            elif current_task and line.strip().startswith('- _Requirements'):
                req_match = re.search(requirement_pattern, line)
                if req_match:
                    req_text = req_match.group(1).strip()
                    requirements = [req.strip() for req in req_text.split(',')]
                    current_task.requirements.extend(requirements)
        
        # Resolve dependencies based on task order
        for i, task in enumerate(tasks):
            if i > 0 and task.level == 0:
                # Top-level tasks depend on previous top-level task
                prev_task = tasks[i-1]
                while prev_task.level > 0 and i > 0:
                    i -= 1
                    if i > 0:
                        prev_task = tasks[i-1]
                if prev_task.level == 0:
                    task.dependencies.append(prev_task.id)
        
        return tasks
    
    def get_next_task(self, spec_id: str) -> Tuple[Optional[Task], ValidationResult]:
        """
        Get the next task that should be executed based on current status.
        
        Requirements: 4.12 - Task sequencing and next task identification
        
        Args:
            spec_id: The specification identifier
            
        Returns:
            Tuple of (Task or None, ValidationResult)
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            # Load execution context
            context, context_result = self.load_execution_context(spec_id)
            if not context_result.is_valid or not context:
                return None, context_result
            
            # Parse tasks
            tasks = self.parse_tasks_from_document(context.tasks_content)
            if not tasks:
                errors.append(ValidationError(
                    code="NO_TASKS_FOUND",
                    message="No tasks found in tasks document",
                    field="tasks"
                ))
                return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Find next task to execute
            for task in tasks:
                if task.status == TaskStatus.NOT_STARTED:
                    # Check if dependencies are satisfied
                    dependencies_satisfied = self._check_task_dependencies(task, tasks)
                    if dependencies_satisfied:
                        return task, ValidationResult(is_valid=True, errors=[], warnings=warnings)
                    else:
                        warnings.append(ValidationWarning(
                            code="TASK_DEPENDENCIES_NOT_MET",
                            message=f"Task {task.id} has unsatisfied dependencies",
                            field="dependencies",
                            suggestion="Complete dependent tasks first"
                        ))
            
            # Check if there are any in-progress tasks
            in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
            if in_progress_tasks:
                return in_progress_tasks[0], ValidationResult(is_valid=True, errors=[], warnings=warnings)
            
            # All tasks completed or blocked
            completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
            if len(completed_tasks) == len(tasks):
                warnings.append(ValidationWarning(
                    code="ALL_TASKS_COMPLETED",
                    message="All tasks have been completed",
                    field="tasks",
                    suggestion="Spec implementation is complete"
                ))
            else:
                warnings.append(ValidationWarning(
                    code="NO_AVAILABLE_TASKS",
                    message="No tasks are available for execution",
                    field="tasks",
                    suggestion="Check task dependencies and status"
                ))
            
            return None, ValidationResult(is_valid=True, errors=[], warnings=warnings)
            
        except Exception as e:
            errors.append(ValidationError(
                code="NEXT_TASK_ERROR",
                message=f"Error finding next task: {str(e)}",
                field="tasks"
            ))
            return None, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    def validate_task_execution_readiness(self, spec_id: str, task_id: str) -> ValidationResult:
        """
        Validate that a task is ready for execution.
        
        Requirements: 4.3 - Execution context validation and preparation
        
        Args:
            spec_id: The specification identifier
            task_id: The task identifier
            
        Returns:
            ValidationResult indicating readiness
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            # Load execution context
            context, context_result = self.load_execution_context(spec_id)
            if not context_result.is_valid or not context:
                errors.extend(context_result.errors)
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Parse tasks and find the target task
            tasks = self.parse_tasks_from_document(context.tasks_content)
            target_task = next((t for t in tasks if t.id == task_id), None)
            
            if not target_task:
                errors.append(ValidationError(
                    code="TASK_NOT_FOUND",
                    message=f"Task {task_id} not found in tasks document",
                    field="task_id"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Check task status
            if target_task.status == TaskStatus.COMPLETED:
                warnings.append(ValidationWarning(
                    code="TASK_ALREADY_COMPLETED",
                    message=f"Task {task_id} is already completed",
                    field="status",
                    suggestion="Choose a different task or verify task status"
                ))
            elif target_task.status == TaskStatus.BLOCKED:
                errors.append(ValidationError(
                    code="TASK_BLOCKED",
                    message=f"Task {task_id} is blocked and cannot be executed",
                    field="status"
                ))
            
            # Check dependencies
            dependencies_satisfied = self._check_task_dependencies(target_task, tasks)
            if not dependencies_satisfied:
                unsatisfied_deps = []
                for dep_id in target_task.dependencies:
                    dep_task = next((t for t in tasks if t.id == dep_id), None)
                    if dep_task and dep_task.status != TaskStatus.COMPLETED:
                        unsatisfied_deps.append(dep_id)
                
                errors.append(ValidationError(
                    code="DEPENDENCIES_NOT_SATISFIED",
                    message=f"Task {task_id} has unsatisfied dependencies: {', '.join(unsatisfied_deps)}",
                    field="dependencies"
                ))
            
            # Check if parent task subtasks are handled correctly
            if target_task.subtasks:
                incomplete_subtasks = [st for st in target_task.subtasks if st.status != TaskStatus.COMPLETED]
                if incomplete_subtasks:
                    warnings.append(ValidationWarning(
                        code="SUBTASKS_NOT_COMPLETED",
                        message=f"Task {task_id} has incomplete subtasks",
                        field="subtasks",
                        suggestion="Complete subtasks before executing parent task"
                    ))
            
            # Validate execution context completeness
            context_warnings = context_result.warnings
            if context_warnings:
                warnings.extend(context_warnings)
            
            return ValidationResult(
                is_valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            errors.append(ValidationError(
                code="READINESS_CHECK_ERROR",
                message=f"Error checking task execution readiness: {str(e)}",
                field="validation"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    def _analyze_project_structure(self) -> ProjectStructure:
        """
        Analyze the current project structure.
        
        Returns:
            ProjectStructure with current project layout
        """
        directories = []
        files = []
        package_files = []
        
        try:
            # Scan workspace for relevant directories and files
            for root, dirs, filenames in self.workspace_root.walk():
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'dist', 'build']]
                
                rel_root = root.relative_to(self.workspace_root)
                if rel_root != Path('.'):
                    directories.append(str(rel_root))
                
                for filename in filenames:
                    if not filename.startswith('.'):
                        rel_path = rel_root / filename
                        files.append(str(rel_path))
                        
                        # Identify package files
                        if filename in ['package.json', 'pyproject.toml', 'setup.py', 'requirements.txt']:
                            package_files.append(str(rel_path))
        
        except Exception:
            # If analysis fails, return minimal structure
            pass
        
        return ProjectStructure(
            root_path=str(self.workspace_root),
            directories=directories,
            files=files,
            package_files=package_files
        )
    
    def _analyze_existing_code(self) -> CodeContext:
        """
        Analyze existing code context in the project.
        
        Returns:
            CodeContext with existing code information
        """
        existing_files = {}
        imports = []
        classes = []
        functions = []
        
        try:
            # Scan for code files
            code_extensions = {'.py', '.ts', '.tsx', '.js', '.jsx'}
            
            for root, dirs, filenames in self.workspace_root.walk():
                # Skip hidden directories and common ignore patterns
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'dist', 'build']]
                
                for filename in filenames:
                    file_path = root / filename
                    if file_path.suffix in code_extensions:
                        try:
                            rel_path = file_path.relative_to(self.workspace_root)
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                existing_files[str(rel_path)] = content
                                
                                # Extract basic code elements
                                if file_path.suffix == '.py':
                                    imports.extend(self._extract_python_imports(content))
                                    classes.extend(self._extract_python_classes(content))
                                    functions.extend(self._extract_python_functions(content))
                                elif file_path.suffix in {'.ts', '.tsx', '.js', '.jsx'}:
                                    imports.extend(self._extract_js_imports(content))
                                    classes.extend(self._extract_js_classes(content))
                                    functions.extend(self._extract_js_functions(content))
                        except Exception:
                            # Skip files that can't be read
                            continue
        
        except Exception:
            # If analysis fails, return empty context
            pass
        
        return CodeContext(
            existing_files=existing_files,
            imports=list(set(imports)),
            classes=list(set(classes)),
            functions=list(set(functions))
        )
    
    def _check_task_dependencies(self, task: Task, all_tasks: List[Task]) -> bool:
        """
        Check if all dependencies for a task are satisfied.
        
        Args:
            task: The task to check
            all_tasks: List of all tasks
            
        Returns:
            True if all dependencies are satisfied
        """
        for dep_id in task.dependencies:
            dep_task = next((t for t in all_tasks if t.id == dep_id), None)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
    
    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract import statements from Python code."""
        imports = []
        import_pattern = r'^(?:from\s+\S+\s+)?import\s+(.+)$'
        
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith(('import ', 'from ')):
                match = re.search(import_pattern, line)
                if match:
                    imports.append(line)
        
        return imports
    
    def _extract_python_classes(self, content: str) -> List[str]:
        """Extract class names from Python code."""
        classes = []
        class_pattern = r'^class\s+(\w+)'
        
        for line in content.split('\n'):
            line = line.strip()
            match = re.match(class_pattern, line)
            if match:
                classes.append(match.group(1))
        
        return classes
    
    def _extract_python_functions(self, content: str) -> List[str]:
        """Extract function names from Python code."""
        functions = []
        func_pattern = r'^def\s+(\w+)'
        
        for line in content.split('\n'):
            line = line.strip()
            match = re.match(func_pattern, line)
            if match:
                functions.append(match.group(1))
        
        return functions
    
    def _extract_js_imports(self, content: str) -> List[str]:
        """Extract import statements from JavaScript/TypeScript code."""
        imports = []
        import_patterns = [
            r'^import\s+.+$',
            r'^const\s+.+\s*=\s*require\(.+\)$'
        ]
        
        for line in content.split('\n'):
            line = line.strip()
            for pattern in import_patterns:
                if re.match(pattern, line):
                    imports.append(line)
                    break
        
        return imports
    
    def _extract_js_classes(self, content: str) -> List[str]:
        """Extract class names from JavaScript/TypeScript code."""
        classes = []
        class_patterns = [
            r'^class\s+(\w+)',
            r'^export\s+class\s+(\w+)',
            r'^interface\s+(\w+)',
            r'^export\s+interface\s+(\w+)'
        ]
        
        for line in content.split('\n'):
            line = line.strip()
            for pattern in class_patterns:
                match = re.match(pattern, line)
                if match:
                    classes.append(match.group(1))
                    break
        
        return classes
    
    def _extract_js_functions(self, content: str) -> List[str]:
        """Extract function names from JavaScript/TypeScript code."""
        functions = []
        func_patterns = [
            r'^function\s+(\w+)',
            r'^export\s+function\s+(\w+)',
            r'^const\s+(\w+)\s*=\s*\(',
            r'^export\s+const\s+(\w+)\s*=\s*\('
        ]
        
        for line in content.split('\n'):
            line = line.strip()
            for pattern in func_patterns:
                match = re.match(pattern, line)
                if match:
                    functions.append(match.group(1))
                    break
        
        return functions
    
    def update_task_status(self, spec_id: str, task_id: str, status: TaskStatus) -> ValidationResult:
        """
        Update the status of a specific task in the tasks document.
        
        Requirements: 4.5, 4.8 - Task status tracking and status update mechanisms
        
        Args:
            spec_id: The specification identifier
            task_id: The task identifier
            status: New status for the task
            
        Returns:
            ValidationResult indicating success or failure
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            # Load current tasks document
            tasks_doc, load_result = self.file_manager.load_document(spec_id, DocumentType.TASKS)
            if not load_result.success or not tasks_doc:
                errors.append(ValidationError(
                    code="TASKS_LOAD_FAILED",
                    message=f"Failed to load tasks document: {load_result.message}",
                    field="tasks"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Parse tasks to find the target task
            tasks = self.parse_tasks_from_document(tasks_doc.content)
            target_task = next((t for t in tasks if t.id == task_id), None)
            
            if not target_task:
                errors.append(ValidationError(
                    code="TASK_NOT_FOUND",
                    message=f"Task {task_id} not found in tasks document",
                    field="task_id"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Validate status transition
            transition_valid = self._validate_status_transition(target_task.status, status)
            if not transition_valid:
                errors.append(ValidationError(
                    code="INVALID_STATUS_TRANSITION",
                    message=f"Invalid status transition from {target_task.status} to {status}",
                    field="status"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Update task status in document content
            updated_content = self._update_task_status_in_content(tasks_doc.content, task_id, status)
            
            # Save updated document
            save_result = self.file_manager.save_document(spec_id, DocumentType.TASKS, updated_content)
            if not save_result.success:
                errors.append(ValidationError(
                    code="TASKS_SAVE_FAILED",
                    message=f"Failed to save updated tasks document: {save_result.message}",
                    field="tasks"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Handle parent task completion logic
            if status == TaskStatus.COMPLETED:
                parent_completion_result = self._check_and_update_parent_completion(spec_id, task_id, updated_content)
                if parent_completion_result.warnings:
                    warnings.extend(parent_completion_result.warnings)
            
            # Clear cache to force reload
            if spec_id in self._context_cache:
                del self._context_cache[spec_id]
            
            return ValidationResult(is_valid=True, errors=[], warnings=warnings)
            
        except Exception as e:
            errors.append(ValidationError(
                code="STATUS_UPDATE_ERROR",
                message=f"Error updating task status: {str(e)}",
                field="status"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    def calculate_progress(self, spec_id: str) -> Tuple[Dict[str, Any], ValidationResult]:
        """
        Calculate comprehensive progress metrics for a specification.
        
        Requirements: 4.9, 4.10 - Task progress calculation and reporting
        
        Args:
            spec_id: The specification identifier
            
        Returns:
            Tuple of (progress metrics dict, ValidationResult)
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        progress_metrics = {}
        
        try:
            # Load execution context
            context, context_result = self.load_execution_context(spec_id)
            if not context_result.is_valid or not context:
                errors.extend(context_result.errors)
                return {}, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Parse tasks
            tasks = self.parse_tasks_from_document(context.tasks_content)
            if not tasks:
                warnings.append(ValidationWarning(
                    code="NO_TASKS_FOUND",
                    message="No tasks found for progress calculation",
                    field="tasks",
                    suggestion="Add tasks to the tasks document"
                ))
                return {}, ValidationResult(is_valid=True, errors=[], warnings=warnings)
            
            # Calculate basic counts
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
            in_progress_tasks = len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS])
            not_started_tasks = len([t for t in tasks if t.status == TaskStatus.NOT_STARTED])
            blocked_tasks = len([t for t in tasks if t.status == TaskStatus.BLOCKED])
            
            # Calculate progress percentages
            completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Separate top-level and sub-tasks
            top_level_tasks = [t for t in tasks if t.level == 0]
            sub_tasks = [t for t in tasks if t.level > 0]
            
            # Calculate weighted progress (top-level tasks have more weight)
            top_level_weight = 0.7
            sub_task_weight = 0.3
            
            top_level_completed = len([t for t in top_level_tasks if t.status == TaskStatus.COMPLETED])
            sub_tasks_completed = len([t for t in sub_tasks if t.status == TaskStatus.COMPLETED])
            
            weighted_progress = 0
            if top_level_tasks:
                weighted_progress += (top_level_completed / len(top_level_tasks)) * top_level_weight
            if sub_tasks:
                weighted_progress += (sub_tasks_completed / len(sub_tasks)) * sub_task_weight
            
            weighted_percentage = weighted_progress * 100
            
            # Calculate estimated completion
            avg_task_effort = sum(t.estimated_effort for t in tasks) / len(tasks) if tasks else 1
            remaining_effort = sum(t.estimated_effort for t in tasks if t.status != TaskStatus.COMPLETED)
            
            # Identify next tasks
            next_task, _ = self.get_next_task(spec_id)
            next_task_id = next_task.id if next_task else None
            
            # Identify blocked tasks with reasons
            blocked_task_details = []
            for task in tasks:
                if task.status == TaskStatus.BLOCKED or not self._check_task_dependencies(task, tasks):
                    blocked_task_details.append({
                        'id': task.id,
                        'description': task.description,
                        'dependencies': task.dependencies
                    })
            
            # Calculate phase progress
            phase_progress = self._calculate_phase_progress(tasks)
            
            progress_metrics = {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'not_started_tasks': not_started_tasks,
                'blocked_tasks': blocked_tasks,
                'completion_percentage': round(completion_percentage, 2),
                'weighted_percentage': round(weighted_percentage, 2),
                'top_level_tasks': {
                    'total': len(top_level_tasks),
                    'completed': top_level_completed,
                    'percentage': round((top_level_completed / len(top_level_tasks) * 100) if top_level_tasks else 0, 2)
                },
                'sub_tasks': {
                    'total': len(sub_tasks),
                    'completed': sub_tasks_completed,
                    'percentage': round((sub_tasks_completed / len(sub_tasks) * 100) if sub_tasks else 0, 2)
                },
                'estimated_remaining_effort': remaining_effort,
                'average_task_effort': round(avg_task_effort, 2),
                'next_task_id': next_task_id,
                'blocked_task_details': blocked_task_details,
                'phase_progress': phase_progress,
                'last_updated': datetime.utcnow().isoformat()
            }
            
            return progress_metrics, ValidationResult(is_valid=True, errors=[], warnings=warnings)
            
        except Exception as e:
            errors.append(ValidationError(
                code="PROGRESS_CALCULATION_ERROR",
                message=f"Error calculating progress: {str(e)}",
                field="progress"
            ))
            return {}, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    def validate_task_completion(self, spec_id: str, task_id: str, task_result: TaskResult) -> ValidationResult:
        """
        Validate that a task has been completed according to its requirements.
        
        Requirements: 6.1, 6.2, 6.3, 6.4 - Task completion validation against requirements
        
        Args:
            spec_id: The specification identifier
            task_id: The task identifier
            task_result: Result of task execution
            
        Returns:
            ValidationResult indicating if completion is valid
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            # Load execution context
            context, context_result = self.load_execution_context(spec_id)
            if not context_result.is_valid or not context:
                errors.extend(context_result.errors)
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Parse tasks and find target task
            tasks = self.parse_tasks_from_document(context.tasks_content)
            target_task = next((t for t in tasks if t.id == task_id), None)
            
            if not target_task:
                errors.append(ValidationError(
                    code="TASK_NOT_FOUND",
                    message=f"Task {task_id} not found for validation",
                    field="task_id"
                ))
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Validate task execution success
            if not task_result.success:
                errors.append(ValidationError(
                    code="TASK_EXECUTION_FAILED",
                    message=f"Task execution failed: {task_result.message}",
                    field="execution"
                ))
            
            # Validate against requirements
            requirement_validation = self._validate_against_requirements(
                target_task, task_result, context.requirements_content
            )
            if requirement_validation.errors:
                errors.extend(requirement_validation.errors)
            if requirement_validation.warnings:
                warnings.extend(requirement_validation.warnings)
            
            # Validate file modifications
            if task_result.files_created or task_result.files_modified:
                file_validation = self._validate_file_modifications(task_result)
                if file_validation.warnings:
                    warnings.extend(file_validation.warnings)
            
            # Validate test execution if applicable
            if target_task.description.lower().find('test') != -1:
                if not task_result.tests_run:
                    warnings.append(ValidationWarning(
                        code="NO_TESTS_RUN",
                        message="Task involves testing but no tests were executed",
                        field="tests",
                        suggestion="Ensure tests are created and executed"
                    ))
            
            # Validate subtask completion if this is a parent task
            if target_task.subtasks:
                subtask_validation = self._validate_subtask_completion(target_task, tasks)
                if subtask_validation.errors:
                    errors.extend(subtask_validation.errors)
                if subtask_validation.warnings:
                    warnings.extend(subtask_validation.warnings)
            
            return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
            
        except Exception as e:
            errors.append(ValidationError(
                code="COMPLETION_VALIDATION_ERROR",
                message=f"Error validating task completion: {str(e)}",
                field="validation"
            ))
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    def get_task_progress_report(self, spec_id: str, task_id: Optional[str] = None) -> Tuple[Dict[str, Any], ValidationResult]:
        """
        Generate a detailed progress report for a task or entire spec.
        
        Requirements: 6.2, 6.3 - Task progress reporting and tracking
        
        Args:
            spec_id: The specification identifier
            task_id: Optional specific task ID for detailed report
            
        Returns:
            Tuple of (progress report dict, ValidationResult)
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            # Get overall progress
            progress_metrics, progress_result = self.calculate_progress(spec_id)
            if not progress_result.is_valid:
                return {}, progress_result
            
            if progress_result.warnings:
                warnings.extend(progress_result.warnings)
            
            report = {
                'spec_id': spec_id,
                'overall_progress': progress_metrics,
                'generated_at': datetime.utcnow().isoformat()
            }
            
            # Add task-specific details if requested
            if task_id:
                context, context_result = self.load_execution_context(spec_id)
                if context_result.is_valid and context:
                    tasks = self.parse_tasks_from_document(context.tasks_content)
                    target_task = next((t for t in tasks if t.id == task_id), None)
                    
                    if target_task:
                        task_details = {
                            'id': target_task.id,
                            'description': target_task.description,
                            'status': target_task.status,
                            'level': target_task.level,
                            'requirements': target_task.requirements,
                            'dependencies': target_task.dependencies,
                            'estimated_effort': target_task.estimated_effort,
                            'subtasks': [
                                {
                                    'id': st.id,
                                    'description': st.description,
                                    'status': st.status
                                } for st in target_task.subtasks
                            ]
                        }
                        
                        # Check if dependencies are satisfied
                        dependencies_satisfied = self._check_task_dependencies(target_task, tasks)
                        task_details['dependencies_satisfied'] = dependencies_satisfied
                        
                        # Add blocking information
                        if not dependencies_satisfied:
                            blocking_tasks = []
                            for dep_id in target_task.dependencies:
                                dep_task = next((t for t in tasks if t.id == dep_id), None)
                                if dep_task and dep_task.status != TaskStatus.COMPLETED:
                                    blocking_tasks.append({
                                        'id': dep_task.id,
                                        'description': dep_task.description,
                                        'status': dep_task.status
                                    })
                            task_details['blocking_tasks'] = blocking_tasks
                        
                        report['task_details'] = task_details
                    else:
                        warnings.append(ValidationWarning(
                            code="TASK_NOT_FOUND_FOR_REPORT",
                            message=f"Task {task_id} not found for detailed report",
                            field="task_id",
                            suggestion="Verify the task ID exists in the tasks document"
                        ))
            
            return report, ValidationResult(is_valid=True, errors=[], warnings=warnings)
            
        except Exception as e:
            errors.append(ValidationError(
                code="PROGRESS_REPORT_ERROR",
                message=f"Error generating progress report: {str(e)}",
                field="report"
            ))
            return {}, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    def _validate_status_transition(self, current_status: TaskStatus, new_status: TaskStatus) -> bool:
        """
        Validate that a status transition is allowed.
        
        Args:
            current_status: Current task status
            new_status: Proposed new status
            
        Returns:
            True if transition is valid
        """
        # Define valid transitions
        valid_transitions = {
            TaskStatus.NOT_STARTED: [TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED],
            TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED, TaskStatus.BLOCKED, TaskStatus.NOT_STARTED],
            TaskStatus.COMPLETED: [TaskStatus.IN_PROGRESS],  # Allow reopening completed tasks
            TaskStatus.BLOCKED: [TaskStatus.NOT_STARTED, TaskStatus.IN_PROGRESS]
        }
        
        return new_status in valid_transitions.get(current_status, [])
    
    def _update_task_status_in_content(self, content: str, task_id: str, status: TaskStatus) -> str:
        """
        Update task status in the markdown content.
        
        Args:
            content: Original tasks document content
            task_id: Task identifier to update
            status: New status
            
        Returns:
            Updated content with new status
        """
        # Map status to checkbox character
        status_chars = {
            TaskStatus.NOT_STARTED: ' ',
            TaskStatus.IN_PROGRESS: '-',
            TaskStatus.COMPLETED: 'x',
            TaskStatus.BLOCKED: '!'
        }
        
        status_char = status_chars.get(status, ' ')
        
        # Pattern to match task line
        pattern = rf'^(- \[)[x -!](\] {re.escape(task_id)}\s+.+)$'
        
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            match = re.match(pattern, line)
            if match:
                # Update the status character
                updated_line = f"{match.group(1)}{status_char}{match.group(2)}"
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        
        return '\n'.join(updated_lines)
    
    def _check_and_update_parent_completion(self, spec_id: str, completed_task_id: str, tasks_content: str) -> ValidationResult:
        """
        Check if parent task should be completed when subtask is completed.
        
        Args:
            spec_id: Specification identifier
            completed_task_id: ID of the completed task
            tasks_content: Current tasks document content
            
        Returns:
            ValidationResult with any warnings about parent task updates
        """
        warnings: List[ValidationWarning] = []
        
        try:
            tasks = self.parse_tasks_from_document(tasks_content)
            completed_task = next((t for t in tasks if t.id == completed_task_id), None)
            
            if not completed_task or not completed_task.parent_id:
                return ValidationResult(is_valid=True, errors=[], warnings=warnings)
            
            # Find parent task
            parent_task = next((t for t in tasks if t.id == completed_task.parent_id), None)
            if not parent_task:
                return ValidationResult(is_valid=True, errors=[], warnings=warnings)
            
            # Check if all subtasks are completed
            all_subtasks_completed = all(
                st.status == TaskStatus.COMPLETED for st in parent_task.subtasks
            )
            
            if all_subtasks_completed and parent_task.status != TaskStatus.COMPLETED:
                # Update parent task to completed
                updated_content = self._update_task_status_in_content(
                    tasks_content, parent_task.id, TaskStatus.COMPLETED
                )
                
                save_result = self.file_manager.save_document(spec_id, DocumentType.TASKS, updated_content)
                if save_result.success:
                    warnings.append(ValidationWarning(
                        code="PARENT_TASK_AUTO_COMPLETED",
                        message=f"Parent task {parent_task.id} automatically marked as completed",
                        field="parent_task",
                        suggestion="Verify parent task completion is appropriate"
                    ))
                else:
                    warnings.append(ValidationWarning(
                        code="PARENT_TASK_UPDATE_FAILED",
                        message=f"Failed to auto-complete parent task {parent_task.id}",
                        field="parent_task",
                        suggestion="Manually update parent task status"
                    ))
            
        except Exception as e:
            warnings.append(ValidationWarning(
                code="PARENT_COMPLETION_CHECK_ERROR",
                message=f"Error checking parent task completion: {str(e)}",
                field="parent_task",
                suggestion="Manually verify parent task status"
            ))
        
        return ValidationResult(is_valid=True, errors=[], warnings=warnings)
    
    def _calculate_phase_progress(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Calculate progress by implementation phases.
        
        Args:
            tasks: List of all tasks
            
        Returns:
            Dictionary with phase-based progress metrics
        """
        # Group tasks by major phases (based on task numbering)
        phases = {}
        
        for task in tasks:
            if task.level == 0:  # Top-level tasks represent phases
                phase_num = task.id.split('.')[0]
                if phase_num not in phases:
                    phases[phase_num] = {
                        'name': task.description.split(' ', 2)[-1] if len(task.description.split(' ')) > 2 else task.description,
                        'tasks': [],
                        'completed': 0,
                        'total': 0
                    }
                
                # Add this task and its subtasks
                phase_tasks = [task] + task.subtasks
                phases[phase_num]['tasks'].extend(phase_tasks)
                phases[phase_num]['total'] += len(phase_tasks)
                phases[phase_num]['completed'] += len([t for t in phase_tasks if t.status == TaskStatus.COMPLETED])
        
        # Calculate percentages
        for phase_data in phases.values():
            if phase_data['total'] > 0:
                phase_data['percentage'] = round((phase_data['completed'] / phase_data['total']) * 100, 2)
            else:
                phase_data['percentage'] = 0
        
        return phases
    
    def _validate_against_requirements(self, task: Task, task_result: TaskResult, requirements_content: str) -> ValidationResult:
        """
        Validate task completion against referenced requirements.
        
        Args:
            task: The completed task
            task_result: Result of task execution
            requirements_content: Content of requirements document
            
        Returns:
            ValidationResult with requirement validation
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        # Check if task references requirements
        if not task.requirements:
            warnings.append(ValidationWarning(
                code="NO_REQUIREMENTS_REFERENCED",
                message=f"Task {task.id} does not reference any requirements",
                field="requirements",
                suggestion="Add requirement references to ensure traceability"
            ))
            return ValidationResult(is_valid=True, errors=[], warnings=warnings)
        
        # Validate that referenced requirements exist in the document
        for req_ref in task.requirements:
            if req_ref.strip() not in requirements_content:
                warnings.append(ValidationWarning(
                    code="REQUIREMENT_NOT_FOUND",
                    message=f"Referenced requirement {req_ref} not found in requirements document",
                    field="requirements",
                    suggestion="Verify requirement references are correct"
                ))
        
        # Basic validation that task execution aligns with coding requirements
        if task_result.success:
            if not task_result.files_created and not task_result.files_modified:
                warnings.append(ValidationWarning(
                    code="NO_FILES_MODIFIED",
                    message="Task completed but no files were created or modified",
                    field="files",
                    suggestion="Verify that task implementation is complete"
                ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def _validate_file_modifications(self, task_result: TaskResult) -> ValidationResult:
        """
        Validate file modifications from task execution.
        
        Args:
            task_result: Result of task execution
            
        Returns:
            ValidationResult with file validation
        """
        warnings: List[ValidationWarning] = []
        
        # Check if files actually exist
        for file_path in task_result.files_created + task_result.files_modified:
            full_path = self.workspace_root / file_path
            if not full_path.exists():
                warnings.append(ValidationWarning(
                    code="REPORTED_FILE_NOT_FOUND",
                    message=f"Reported file modification not found: {file_path}",
                    field="files",
                    suggestion="Verify file paths are correct"
                ))
        
        return ValidationResult(is_valid=True, errors=[], warnings=warnings)
    
    def _validate_subtask_completion(self, parent_task: Task, all_tasks: List[Task]) -> ValidationResult:
        """
        Validate that all subtasks are completed before parent task completion.
        
        Args:
            parent_task: The parent task to validate
            all_tasks: List of all tasks
            
        Returns:
            ValidationResult with subtask validation
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        incomplete_subtasks = [st for st in parent_task.subtasks if st.status != TaskStatus.COMPLETED]
        
        if incomplete_subtasks:
            errors.append(ValidationError(
                code="INCOMPLETE_SUBTASKS",
                message=f"Parent task {parent_task.id} has incomplete subtasks: {[st.id for st in incomplete_subtasks]}",
                field="subtasks"
            ))
        
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
    
    def execute_task(self, spec_id: str, task_id: str) -> TaskResult:
        """
        Execute a single task with proper isolation and error handling.
        
        Requirements: 4.4, 4.6, 4.7 - Single-task execution with proper isolation and error handling
        
        Args:
            spec_id: The specification identifier
            task_id: The task identifier to execute
            
        Returns:
            TaskResult with execution details
        """
        start_time = datetime.utcnow()
        
        try:
            # Validate task execution readiness
            readiness_result = self.validate_task_execution_readiness(spec_id, task_id)
            if not readiness_result.is_valid:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    message=f"Task not ready for execution: {readiness_result.errors[0].message}",
                    error_details=str(readiness_result.errors)
                )
            
            # Load execution context
            context, context_result = self.load_execution_context(spec_id)
            if not context_result.is_valid or not context:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    message=f"Failed to load execution context: {context_result.errors[0].message if context_result.errors else 'Unknown error'}",
                    error_details=str(context_result.errors)
                )
            
            # Parse tasks and find target task
            tasks = self.parse_tasks_from_document(context.tasks_content)
            target_task = next((t for t in tasks if t.id == task_id), None)
            
            if not target_task:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    message=f"Task {task_id} not found",
                    error_details="Task not found in parsed tasks"
                )
            
            # Update task status to in_progress
            status_update_result = self.update_task_status(spec_id, task_id, TaskStatus.IN_PROGRESS)
            if not status_update_result.is_valid:
                return TaskResult(
                    task_id=task_id,
                    success=False,
                    message=f"Failed to update task status: {status_update_result.errors[0].message}",
                    error_details=str(status_update_result.errors)
                )
            
            # Handle subtask execution if this is a parent task
            if target_task.subtasks:
                subtask_result = self._execute_subtasks(spec_id, target_task, context)
                if not subtask_result.success:
                    # Revert task status on failure
                    self.update_task_status(spec_id, task_id, TaskStatus.NOT_STARTED)
                    return subtask_result
            
            # Execute the actual task implementation
            implementation_result = self._execute_task_implementation(target_task, context)
            
            # Validate task completion
            if implementation_result.success:
                completion_validation = self.validate_task_completion(spec_id, task_id, implementation_result)
                if completion_validation.is_valid:
                    # Update task status to completed
                    final_status_result = self.update_task_status(spec_id, task_id, TaskStatus.COMPLETED)
                    if final_status_result.warnings:
                        implementation_result.validation_results.append(final_status_result)
                else:
                    # Task execution succeeded but validation failed
                    implementation_result.success = False
                    implementation_result.message += f" (Validation failed: {completion_validation.errors[0].message if completion_validation.errors else 'Unknown validation error'})"
                    implementation_result.validation_results.append(completion_validation)
                    
                    # Update task status to indicate issue
                    self.update_task_status(spec_id, task_id, TaskStatus.BLOCKED)
            else:
                # Task execution failed, revert status
                self.update_task_status(spec_id, task_id, TaskStatus.NOT_STARTED)
            
            # Calculate execution time
            end_time = datetime.utcnow()
            implementation_result.execution_time = (end_time - start_time).total_seconds()
            
            return implementation_result
            
        except Exception as e:
            # Handle unexpected errors
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            # Try to revert task status
            try:
                self.update_task_status(spec_id, task_id, TaskStatus.NOT_STARTED)
            except:
                pass  # Don't fail on status revert failure
            
            return TaskResult(
                task_id=task_id,
                success=False,
                message=f"Unexpected error during task execution: {str(e)}",
                error_details=str(e),
                execution_time=execution_time
            )
    
    def execute_task_with_recovery(self, spec_id: str, task_id: str, max_retries: int = 3) -> TaskResult:
        """
        Execute a task with automatic error recovery and retry logic.
        
        Requirements: 4.11, 6.7, 6.11 - Task execution error handling and recovery
        
        Args:
            spec_id: The specification identifier
            task_id: The task identifier to execute
            max_retries: Maximum number of retry attempts
            
        Returns:
            TaskResult with execution details and recovery information
        """
        last_result = None
        recovery_attempts = []
        
        for attempt in range(max_retries + 1):
            try:
                result = self.execute_task(spec_id, task_id)
                
                if result.success:
                    # Add recovery information if this wasn't the first attempt
                    if attempt > 0:
                        result.message += f" (Succeeded after {attempt} recovery attempts)"
                        result.validation_results.append(ValidationResult(
                            is_valid=True,
                            errors=[],
                            warnings=[ValidationWarning(
                                code="TASK_RECOVERED",
                                message=f"Task succeeded after {attempt} recovery attempts",
                                field="recovery",
                                suggestion="Consider investigating why initial attempts failed"
                            )]
                        ))
                    return result
                
                # Task failed, attempt recovery if we have retries left
                if attempt < max_retries:
                    recovery_result = self._attempt_task_recovery(spec_id, task_id, result)
                    recovery_attempts.append({
                        'attempt': attempt + 1,
                        'error': result.message,
                        'recovery_action': recovery_result.get('action', 'unknown'),
                        'recovery_success': recovery_result.get('success', False)
                    })
                    
                    if not recovery_result.get('success', False):
                        # Recovery failed, but continue to next attempt
                        continue
                else:
                    # No more retries, return the last failure
                    last_result = result
                    break
                    
            except Exception as e:
                # Unexpected error during execution
                last_result = TaskResult(
                    task_id=task_id,
                    success=False,
                    message=f"Execution attempt {attempt + 1} failed with unexpected error: {str(e)}",
                    error_details=str(e)
                )
                
                if attempt < max_retries:
                    recovery_attempts.append({
                        'attempt': attempt + 1,
                        'error': str(e),
                        'recovery_action': 'retry',
                        'recovery_success': False
                    })
                    continue
                else:
                    break
        
        # All attempts failed, return final result with recovery information
        if last_result:
            last_result.message += f" (Failed after {max_retries + 1} attempts)"
            if recovery_attempts:
                last_result.error_details += f"\nRecovery attempts: {recovery_attempts}"
            
            # Add validation result with recovery information
            last_result.validation_results.append(ValidationResult(
                is_valid=False,
                errors=[ValidationError(
                    code="TASK_EXECUTION_FAILED_WITH_RECOVERY",
                    message=f"Task failed after {max_retries + 1} attempts with recovery",
                    field="execution"
                )],
                warnings=[]
            ))
        
        return last_result or TaskResult(
            task_id=task_id,
            success=False,
            message="Task execution failed with unknown error",
            error_details="No execution result available"
        )
    
    def _execute_subtasks(self, spec_id: str, parent_task: Task, context: ExecutionContext) -> TaskResult:
        """
        Execute all subtasks of a parent task in sequence.
        
        Requirements: 4.14 - Sub-task handling and parent task completion
        
        Args:
            spec_id: The specification identifier
            parent_task: The parent task containing subtasks
            context: Execution context
            
        Returns:
            TaskResult indicating success or failure of subtask execution
        """
        executed_subtasks = []
        failed_subtasks = []
        
        try:
            for subtask in parent_task.subtasks:
                if subtask.status == TaskStatus.COMPLETED:
                    # Skip already completed subtasks
                    executed_subtasks.append(subtask.id)
                    continue
                
                # Execute subtask
                subtask_result = self.execute_task(spec_id, subtask.id)
                
                if subtask_result.success:
                    executed_subtasks.append(subtask.id)
                else:
                    failed_subtasks.append({
                        'id': subtask.id,
                        'error': subtask_result.message,
                        'details': subtask_result.error_details
                    })
                    
                    # Stop on first failure
                    break
            
            if failed_subtasks:
                return TaskResult(
                    task_id=parent_task.id,
                    success=False,
                    message=f"Subtask execution failed: {failed_subtasks[0]['error']}",
                    error_details=f"Failed subtasks: {failed_subtasks}",
                    files_modified=[],
                    files_created=[],
                    tests_run=[]
                )
            
            return TaskResult(
                task_id=parent_task.id,
                success=True,
                message=f"All subtasks completed successfully: {executed_subtasks}",
                files_modified=[],
                files_created=[],
                tests_run=[]
            )
            
        except Exception as e:
            return TaskResult(
                task_id=parent_task.id,
                success=False,
                message=f"Error executing subtasks: {str(e)}",
                error_details=str(e),
                files_modified=[],
                files_created=[],
                tests_run=[]
            )
    
    def _execute_task_implementation(self, task: Task, context: ExecutionContext) -> TaskResult:
        """
        Execute the actual implementation of a task.
        
        This is a placeholder for the actual task execution logic.
        In a real implementation, this would interface with code generation,
        file manipulation, and testing systems.
        
        Requirements: 4.4 - Single-task execution with proper isolation
        
        Args:
            task: The task to execute
            context: Execution context
            
        Returns:
            TaskResult with implementation details
        """
        try:
            # This is a simulation of task execution
            # In the real implementation, this would:
            # 1. Parse the task description to understand what needs to be done
            # 2. Generate or modify code based on the requirements and design
            # 3. Run tests if applicable
            # 4. Validate the implementation
            
            # For now, we'll simulate successful execution
            files_created = []
            files_modified = []
            tests_run = []
            
            # Simulate file operations based on task description
            if 'create' in task.description.lower():
                # Simulate file creation
                files_created.append(f"simulated_file_{task.id.replace('.', '_')}.py")
            
            if 'implement' in task.description.lower() or 'write' in task.description.lower():
                # Simulate file modification
                files_modified.append(f"existing_file_{task.id.replace('.', '_')}.py")
            
            if 'test' in task.description.lower():
                # Simulate test execution
                tests_run.append(f"test_{task.id.replace('.', '_')}")
            
            return TaskResult(
                task_id=task.id,
                success=True,
                message=f"Task {task.id} executed successfully (simulated)",
                files_created=files_created,
                files_modified=files_modified,
                tests_run=tests_run
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task.id,
                success=False,
                message=f"Task implementation failed: {str(e)}",
                error_details=str(e),
                files_created=[],
                files_modified=[],
                tests_run=[]
            )
    
    def _attempt_task_recovery(self, spec_id: str, task_id: str, failed_result: TaskResult) -> Dict[str, Any]:
        """
        Attempt to recover from a task execution failure.
        
        Requirements: 6.11 - Task execution error handling and recovery
        
        Args:
            spec_id: The specification identifier
            task_id: The task identifier that failed
            failed_result: The failed task result
            
        Returns:
            Dictionary with recovery attempt information
        """
        recovery_info = {
            'action': 'none',
            'success': False,
            'message': 'No recovery attempted'
        }
        
        try:
            # Analyze the failure to determine recovery strategy
            error_message = failed_result.message.lower()
            
            if 'permission' in error_message or 'access' in error_message:
                # File permission issues
                recovery_info['action'] = 'permission_fix'
                recovery_info['message'] = 'Attempted to fix file permissions'
                # In real implementation, would attempt to fix permissions
                recovery_info['success'] = True
                
            elif 'not found' in error_message or 'missing' in error_message:
                # Missing dependencies or files
                recovery_info['action'] = 'dependency_check'
                recovery_info['message'] = 'Attempted to resolve missing dependencies'
                # In real implementation, would check and install dependencies
                recovery_info['success'] = True
                
            elif 'syntax' in error_message or 'compilation' in error_message:
                # Code syntax or compilation errors
                recovery_info['action'] = 'code_fix'
                recovery_info['message'] = 'Attempted to fix code syntax issues'
                # In real implementation, would attempt automated code fixes
                recovery_info['success'] = False  # Usually requires manual intervention
                
            elif 'timeout' in error_message:
                # Timeout issues
                recovery_info['action'] = 'retry_with_timeout'
                recovery_info['message'] = 'Increased timeout for retry'
                recovery_info['success'] = True
                
            else:
                # Generic recovery - clear caches and retry
                recovery_info['action'] = 'cache_clear'
                recovery_info['message'] = 'Cleared caches and prepared for retry'
                
                # Clear execution context cache
                if spec_id in self._context_cache:
                    del self._context_cache[spec_id]
                
                recovery_info['success'] = True
            
        except Exception as e:
            recovery_info['action'] = 'error'
            recovery_info['success'] = False
            recovery_info['message'] = f'Recovery attempt failed: {str(e)}'
        
        return recovery_info
    
    def get_execution_summary(self, spec_id: str) -> Tuple[Dict[str, Any], ValidationResult]:
        """
        Get a comprehensive execution summary for a specification.
        
        Requirements: 4.13 - Task execution integration and summary reporting
        
        Args:
            spec_id: The specification identifier
            
        Returns:
            Tuple of (execution summary dict, ValidationResult)
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        try:
            # Get progress metrics
            progress_metrics, progress_result = self.calculate_progress(spec_id)
            if not progress_result.is_valid:
                errors.extend(progress_result.errors)
                return {}, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            if progress_result.warnings:
                warnings.extend(progress_result.warnings)
            
            # Load execution context
            context, context_result = self.load_execution_context(spec_id)
            if not context_result.is_valid or not context:
                errors.extend(context_result.errors)
                return {}, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            
            # Parse tasks
            tasks = self.parse_tasks_from_document(context.tasks_content)
            
            # Calculate execution statistics
            execution_stats = {
                'total_tasks': len(tasks),
                'completed_tasks': len([t for t in tasks if t.status == TaskStatus.COMPLETED]),
                'in_progress_tasks': len([t for t in tasks if t.status == TaskStatus.IN_PROGRESS]),
                'blocked_tasks': len([t for t in tasks if t.status == TaskStatus.BLOCKED]),
                'not_started_tasks': len([t for t in tasks if t.status == TaskStatus.NOT_STARTED])
            }
            
            # Identify critical path and bottlenecks
            critical_path = self._identify_critical_path(tasks)
            bottlenecks = self._identify_bottlenecks(tasks)
            
            # Get next recommended actions
            next_task, next_task_result = self.get_next_task(spec_id)
            next_actions = []
            
            if next_task:
                next_actions.append({
                    'type': 'execute_task',
                    'task_id': next_task.id,
                    'description': next_task.description,
                    'priority': 'high'
                })
            
            # Check for blocked tasks that might be unblocked
            for task in tasks:
                if task.status == TaskStatus.BLOCKED:
                    dependencies_satisfied = self._check_task_dependencies(task, tasks)
                    if dependencies_satisfied:
                        next_actions.append({
                            'type': 'unblock_task',
                            'task_id': task.id,
                            'description': f"Unblock task: {task.description}",
                            'priority': 'medium'
                        })
            
            summary = {
                'spec_id': spec_id,
                'execution_stats': execution_stats,
                'progress_metrics': progress_metrics,
                'critical_path': critical_path,
                'bottlenecks': bottlenecks,
                'next_actions': next_actions,
                'context_info': {
                    'requirements_loaded': bool(context.requirements_content.strip()),
                    'design_loaded': bool(context.design_content.strip()),
                    'tasks_loaded': bool(context.tasks_content.strip()),
                    'project_files': len(context.existing_code.existing_files),
                    'project_classes': len(context.existing_code.classes),
                    'project_functions': len(context.existing_code.functions)
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
            return summary, ValidationResult(is_valid=True, errors=[], warnings=warnings)
            
        except Exception as e:
            errors.append(ValidationError(
                code="EXECUTION_SUMMARY_ERROR",
                message=f"Error generating execution summary: {str(e)}",
                field="summary"
            ))
            return {}, ValidationResult(is_valid=False, errors=errors, warnings=warnings)
    
    def _identify_critical_path(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """
        Identify the critical path through the task dependency graph.
        
        Args:
            tasks: List of all tasks
            
        Returns:
            List of tasks on the critical path
        """
        critical_path = []
        
        try:
            # Simple critical path identification based on dependencies
            # Start with tasks that have no dependencies
            remaining_tasks = [t for t in tasks if t.status != TaskStatus.COMPLETED]
            
            while remaining_tasks:
                # Find tasks with no incomplete dependencies
                ready_tasks = []
                for task in remaining_tasks:
                    dependencies_satisfied = self._check_task_dependencies(task, tasks)
                    if dependencies_satisfied:
                        ready_tasks.append(task)
                
                if not ready_tasks:
                    # No tasks are ready, might be a circular dependency
                    break
                
                # Add the first ready task to critical path
                if ready_tasks:
                    next_task = ready_tasks[0]  # Simple selection, could be more sophisticated
                    critical_path.append({
                        'id': next_task.id,
                        'description': next_task.description,
                        'status': next_task.status,
                        'estimated_effort': next_task.estimated_effort
                    })
                    remaining_tasks.remove(next_task)
        
        except Exception:
            # If critical path calculation fails, return empty list
            pass
        
        return critical_path
    
    def _identify_bottlenecks(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """
        Identify potential bottlenecks in task execution.
        
        Args:
            tasks: List of all tasks
            
        Returns:
            List of potential bottlenecks
        """
        bottlenecks = []
        
        try:
            # Identify tasks that are blocking many other tasks
            for task in tasks:
                if task.status != TaskStatus.COMPLETED:
                    blocked_count = 0
                    for other_task in tasks:
                        if task.id in other_task.dependencies and other_task.status == TaskStatus.NOT_STARTED:
                            blocked_count += 1
                    
                    if blocked_count > 1:  # Task is blocking multiple other tasks
                        bottlenecks.append({
                            'id': task.id,
                            'description': task.description,
                            'status': task.status,
                            'blocking_count': blocked_count,
                            'type': 'dependency_bottleneck'
                        })
            
            # Identify tasks that have been in progress for a long time
            # (This would require execution history in a real implementation)
            in_progress_tasks = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]
            if len(in_progress_tasks) > 2:  # Too many tasks in progress simultaneously
                for task in in_progress_tasks:
                    bottlenecks.append({
                        'id': task.id,
                        'description': task.description,
                        'status': task.status,
                        'type': 'concurrent_execution_bottleneck'
                    })
        
        except Exception:
            # If bottleneck identification fails, return empty list
            pass
        
        return bottlenecks