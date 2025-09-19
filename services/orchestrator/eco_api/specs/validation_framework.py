"""
Comprehensive validation framework for spec-driven workflows.

This module provides validation rules, error reporting, and recovery procedures
for all components in the spec workflow system.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union, Type
from pydantic import BaseModel, Field, validator
import re
import json
from pathlib import Path

from .models import (
    WorkflowPhase, WorkflowStatus, TaskStatus, DocumentType,
    ValidationResult, ValidationError, ValidationWarning,
    SpecMetadata, DocumentMetadata
)


class ValidationType(str, Enum):
    """Types of validation checks."""
    STRUCTURE = "structure"
    CONTENT = "content"
    FORMAT = "format"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"
    TRACEABILITY = "traceability"
    WORKFLOW = "workflow"
    FILE_SYSTEM = "file_system"


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationRule(BaseModel):
    """Definition of a validation rule."""
    id: str
    name: str
    description: str
    type: ValidationType
    severity: ValidationSeverity
    applicable_phases: List[WorkflowPhase] = Field(default_factory=list)
    applicable_documents: List[DocumentType] = Field(default_factory=list)
    enabled: bool = True


class ValidationIssue(BaseModel):
    """A specific validation issue found during validation."""
    rule_id: str
    severity: ValidationSeverity
    message: str
    location: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    suggestion: Optional[str] = None
    auto_fixable: bool = False


class ValidationReport(BaseModel):
    """Comprehensive validation report."""
    spec_id: str
    validation_time: datetime
    overall_status: str  # "valid", "warnings", "errors"
    issues: List[ValidationIssue] = Field(default_factory=list)
    rules_checked: List[str] = Field(default_factory=list)
    summary: Dict[str, int] = Field(default_factory=dict)
    
    def has_errors(self) -> bool:
        """Check if report contains any errors."""
        return any(issue.severity == ValidationSeverity.ERROR for issue in self.issues)
    
    def has_warnings(self) -> bool:
        """Check if report contains any warnings."""
        return any(issue.severity == ValidationSeverity.WARNING for issue in self.issues)
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues filtered by severity."""
        return [issue for issue in self.issues if issue.severity == severity]


class BaseValidator(ABC):
    """Base class for all validators."""
    
    def __init__(self, rule: ValidationRule):
        self.rule = rule
    
    @abstractmethod
    def validate(self, content: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate content and return list of issues."""
        pass
    
    def is_applicable(self, phase: WorkflowPhase, document_type: Optional[DocumentType] = None) -> bool:
        """Check if this validator is applicable to the given phase and document type."""
        if self.rule.applicable_phases and phase not in self.rule.applicable_phases:
            return False
        
        if (document_type and 
            self.rule.applicable_documents and 
            document_type not in self.rule.applicable_documents):
            return False
        
        return self.rule.enabled


class StructureValidator(BaseValidator):
    """Validates document structure and format."""
    
    def validate(self, content: str, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate document structure."""
        issues = []
        document_type = context.get('document_type')
        
        if document_type == DocumentType.REQUIREMENTS:
            issues.extend(self._validate_requirements_structure(content, context))
        elif document_type == DocumentType.DESIGN:
            issues.extend(self._validate_design_structure(content, context))
        elif document_type == DocumentType.TASKS:
            issues.extend(self._validate_tasks_structure(content, context))
        
        return issues
    
    def _validate_requirements_structure(self, content: str, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate requirements document structure."""
        issues = []
        
        # Check for required sections
        required_sections = ["# Requirements Document", "## Introduction", "## Requirements"]
        for section in required_sections:
            if section not in content:
                issues.append(ValidationIssue(
                    rule_id=self.rule.id,
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required section: {section}",
                    suggestion=f"Add the {section} section to the document"
                ))
        
        # Check for proper requirement numbering
        requirement_pattern = r"### Requirement \d+"
        requirements = re.findall(requirement_pattern, content)
        if not requirements:
            issues.append(ValidationIssue(
                rule_id=self.rule.id,
                severity=ValidationSeverity.ERROR,
                message="No properly numbered requirements found",
                suggestion="Add requirements with format '### Requirement 1'"
            ))
        
        # Check for user stories
        user_story_pattern = r"\*\*User Story:\*\* As a .+, I want .+(?:, so that .+)?"
        user_stories = re.findall(user_story_pattern, content, re.DOTALL)
        if len(user_stories) < len(requirements):
            issues.append(ValidationIssue(
                rule_id=self.rule.id,
                severity=ValidationSeverity.WARNING,
                message="Some requirements may be missing user stories",
                suggestion="Ensure each requirement has a user story"
            ))
        
        # Check for acceptance criteria
        if "#### Acceptance Criteria" not in content:
            issues.append(ValidationIssue(
                rule_id=self.rule.id,
                severity=ValidationSeverity.ERROR,
                message="No acceptance criteria sections found",
                suggestion="Add acceptance criteria for each requirement"
            ))
        
        return issues
    
    def _validate_design_structure(self, content: str, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate design document structure."""
        issues = []
        
        # Check for required sections
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
            if section not in content:
                issues.append(ValidationIssue(
                    rule_id=self.rule.id,
                    severity=ValidationSeverity.ERROR,
                    message=f"Missing required section: {section}",
                    suggestion=f"Add the {section} section to the document"
                ))
        
        return issues
    
    def _validate_tasks_structure(self, content: str, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate tasks document structure."""
        issues = []
        
        # Check for implementation plan header
        if "# Implementation Plan" not in content:
            issues.append(ValidationIssue(
                rule_id=self.rule.id,
                severity=ValidationSeverity.ERROR,
                message="Missing implementation plan header",
                suggestion="Add '# Implementation Plan' header"
            ))
        
        # Check for checkbox tasks
        checkbox_pattern = r"- \[[ x]\] \d+\."
        tasks = re.findall(checkbox_pattern, content)
        if not tasks:
            issues.append(ValidationIssue(
                rule_id=self.rule.id,
                severity=ValidationSeverity.ERROR,
                message="No properly formatted tasks found",
                suggestion="Add tasks with format '- [ ] 1. Task description'"
            ))
        
        return issues


class ContentValidator(BaseValidator):
    """Validates document content quality and completeness."""
    
    def validate(self, content: str, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate document content."""
        issues = []
        
        # Check content length
        if len(content.strip()) < 100:
            issues.append(ValidationIssue(
                rule_id=self.rule.id,
                severity=ValidationSeverity.WARNING,
                message="Document content appears to be very short",
                suggestion="Ensure document contains sufficient detail"
            ))
        
        # Check for placeholder text
        placeholders = ["TODO", "TBD", "[placeholder]", "FIXME"]
        for placeholder in placeholders:
            if placeholder.lower() in content.lower():
                issues.append(ValidationIssue(
                    rule_id=self.rule.id,
                    severity=ValidationSeverity.WARNING,
                    message=f"Document contains placeholder text: {placeholder}",
                    suggestion=f"Replace placeholder '{placeholder}' with actual content"
                ))
        
        return issues


class FormatValidator(BaseValidator):
    """Validates document formatting and markdown syntax."""
    
    def validate(self, content: str, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate document formatting."""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for proper header formatting
            if line.startswith('#'):
                if not line.startswith('# ') and not re.match(r'^#+\s', line):
                    issues.append(ValidationIssue(
                        rule_id=self.rule.id,
                        severity=ValidationSeverity.WARNING,
                        message="Header should have space after #",
                        line_number=i,
                        suggestion="Add space after # in headers"
                    ))
            
            # Check for proper list formatting
            if re.match(r'^\d+\.', line.strip()) and not line.startswith('  '):
                if i > 1 and not lines[i-2].strip():  # Check if previous line is empty
                    continue
                if not re.match(r'^\d+\.\s', line.strip()):
                    issues.append(ValidationIssue(
                        rule_id=self.rule.id,
                        severity=ValidationSeverity.WARNING,
                        message="Numbered list item should have space after number",
                        line_number=i,
                        suggestion="Add space after number in list items"
                    ))
        
        return issues


class ConsistencyValidator(BaseValidator):
    """Validates consistency across documents and within documents."""
    
    def validate(self, content: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate document consistency."""
        issues = []
        
        if isinstance(content, dict) and 'documents' in content:
            # Cross-document consistency validation
            documents = content['documents']
            issues.extend(self._validate_cross_document_consistency(documents, context))
        elif isinstance(content, str):
            # Single document consistency validation
            issues.extend(self._validate_single_document_consistency(content, context))
        
        return issues
    
    def _validate_cross_document_consistency(self, documents: Dict[str, str], context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate consistency across multiple documents."""
        issues = []
        
        requirements_content = documents.get('requirements', '')
        design_content = documents.get('design', '')
        tasks_content = documents.get('tasks', '')
        
        # Extract requirement IDs from requirements document
        req_pattern = r"### Requirement (\d+)"
        requirement_ids = set(re.findall(req_pattern, requirements_content))
        
        # Check if design references requirements
        if design_content and requirement_ids:
            referenced_reqs = set()
            for req_id in requirement_ids:
                if f"Requirement {req_id}" in design_content or f"{req_id}." in design_content:
                    referenced_reqs.add(req_id)
            
            unreferenced = requirement_ids - referenced_reqs
            if unreferenced:
                issues.append(ValidationIssue(
                    rule_id=self.rule.id,
                    severity=ValidationSeverity.WARNING,
                    message=f"Requirements not referenced in design: {', '.join(unreferenced)}",
                    suggestion="Ensure all requirements are addressed in the design"
                ))
        
        # Check if tasks reference requirements
        if tasks_content and requirement_ids:
            task_req_pattern = r"_Requirements: ([\d\., ]+)_"
            task_requirements = re.findall(task_req_pattern, tasks_content)
            
            referenced_in_tasks = set()
            for req_list in task_requirements:
                for req_ref in req_list.split(','):
                    req_ref = req_ref.strip()
                    if '.' in req_ref:
                        req_ref = req_ref.split('.')[0]
                    if req_ref.isdigit():
                        referenced_in_tasks.add(req_ref)
            
            unreferenced_in_tasks = requirement_ids - referenced_in_tasks
            if unreferenced_in_tasks:
                issues.append(ValidationIssue(
                    rule_id=self.rule.id,
                    severity=ValidationSeverity.WARNING,
                    message=f"Requirements not referenced in tasks: {', '.join(unreferenced_in_tasks)}",
                    suggestion="Ensure all requirements are covered by implementation tasks"
                ))
        
        return issues
    
    def _validate_single_document_consistency(self, content: str, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate consistency within a single document."""
        issues = []
        
        # Check for consistent numbering
        document_type = context.get('document_type')
        
        if document_type == DocumentType.REQUIREMENTS:
            # Check requirement numbering consistency
            req_pattern = r"### Requirement (\d+)"
            requirement_numbers = [int(match) for match in re.findall(req_pattern, content)]
            
            if requirement_numbers:
                expected = list(range(1, len(requirement_numbers) + 1))
                if requirement_numbers != expected:
                    issues.append(ValidationIssue(
                        rule_id=self.rule.id,
                        severity=ValidationSeverity.ERROR,
                        message="Requirement numbering is not sequential",
                        suggestion="Ensure requirements are numbered sequentially starting from 1"
                    ))
        
        elif document_type == DocumentType.TASKS:
            # Check task numbering consistency
            task_pattern = r"- \[[ x]\] (\d+)\."
            task_numbers = [int(match) for match in re.findall(task_pattern, content)]
            
            if task_numbers:
                # Check for gaps in numbering
                unique_numbers = sorted(set(task_numbers))
                if unique_numbers != list(range(1, max(unique_numbers) + 1)):
                    issues.append(ValidationIssue(
                        rule_id=self.rule.id,
                        severity=ValidationSeverity.WARNING,
                        message="Task numbering has gaps",
                        suggestion="Consider using sequential task numbering"
                    ))
        
        return issues


class TraceabilityValidator(BaseValidator):
    """Validates requirement traceability across documents."""
    
    def validate(self, content: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate requirement traceability."""
        issues = []
        
        if not isinstance(content, dict) or 'documents' not in content:
            return issues
        
        documents = content['documents']
        requirements_content = documents.get('requirements', '')
        tasks_content = documents.get('tasks', '')
        
        if not requirements_content or not tasks_content:
            return issues
        
        # Extract requirements and their sub-requirements
        req_pattern = r"### Requirement (\d+)"
        acceptance_pattern = r"(\d+)\.\s+(?:WHEN|IF|GIVEN)"
        
        requirements = re.findall(req_pattern, requirements_content)
        
        # Find all acceptance criteria
        all_acceptance_criteria = set()
        current_req = None
        
        for line in requirements_content.split('\n'):
            req_match = re.match(r"### Requirement (\d+)", line)
            if req_match:
                current_req = req_match.group(1)
            
            acceptance_match = re.match(r"(\d+)\.\s+(?:WHEN|IF|GIVEN)", line.strip())
            if acceptance_match and current_req:
                criterion_id = f"{current_req}.{acceptance_match.group(1)}"
                all_acceptance_criteria.add(criterion_id)
        
        # Check traceability in tasks
        task_req_pattern = r"_Requirements: ([\d\., ]+)_"
        referenced_criteria = set()
        
        for req_list in re.findall(task_req_pattern, tasks_content):
            for req_ref in req_list.split(','):
                req_ref = req_ref.strip()
                if re.match(r'\d+\.\d+', req_ref):
                    referenced_criteria.add(req_ref)
        
        # Find unreferenced acceptance criteria
        unreferenced = all_acceptance_criteria - referenced_criteria
        if unreferenced:
            issues.append(ValidationIssue(
                rule_id=self.rule.id,
                severity=ValidationSeverity.WARNING,
                message=f"Acceptance criteria not traced to tasks: {', '.join(sorted(unreferenced))}",
                suggestion="Ensure all acceptance criteria are covered by implementation tasks"
            ))
        
        return issues


class WorkflowValidator(BaseValidator):
    """Validates workflow state and transitions."""
    
    def validate(self, content: Any, context: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate workflow state."""
        issues = []
        
        current_phase = context.get('current_phase')
        workflow_status = context.get('workflow_status')
        documents = context.get('documents', {})
        
        # Check phase prerequisites
        if current_phase == WorkflowPhase.DESIGN:
            if not documents.get('requirements'):
                issues.append(ValidationIssue(
                    rule_id=self.rule.id,
                    severity=ValidationSeverity.ERROR,
                    message="Cannot proceed to design phase without approved requirements",
                    suggestion="Complete and approve requirements before proceeding to design"
                ))
        
        elif current_phase == WorkflowPhase.TASKS:
            if not documents.get('requirements') or not documents.get('design'):
                issues.append(ValidationIssue(
                    rule_id=self.rule.id,
                    severity=ValidationSeverity.ERROR,
                    message="Cannot proceed to tasks phase without approved requirements and design",
                    suggestion="Complete and approve requirements and design before proceeding to tasks"
                ))
        
        elif current_phase == WorkflowPhase.EXECUTION:
            if not all(documents.get(doc_type) for doc_type in ['requirements', 'design', 'tasks']):
                issues.append(ValidationIssue(
                    rule_id=self.rule.id,
                    severity=ValidationSeverity.ERROR,
                    message="Cannot proceed to execution phase without all documents",
                    suggestion="Complete and approve all documents before proceeding to execution"
                ))
        
        return issues


class ValidationFramework:
    """
    Comprehensive validation framework for spec-driven workflows.
    
    Provides validation rules, error reporting, and recovery procedures
    for all components in the system.
    """
    
    def __init__(self):
        self.validators: Dict[str, BaseValidator] = {}
        self.rules: Dict[str, ValidationRule] = {}
        self._setup_default_rules()
        self._setup_validators()
    
    def _setup_default_rules(self) -> None:
        """Set up default validation rules."""
        rules = [
            ValidationRule(
                id="structure_requirements",
                name="Requirements Structure",
                description="Validate requirements document structure and format",
                type=ValidationType.STRUCTURE,
                severity=ValidationSeverity.ERROR,
                applicable_phases=[WorkflowPhase.REQUIREMENTS],
                applicable_documents=[DocumentType.REQUIREMENTS]
            ),
            ValidationRule(
                id="structure_design",
                name="Design Structure",
                description="Validate design document structure and format",
                type=ValidationType.STRUCTURE,
                severity=ValidationSeverity.ERROR,
                applicable_phases=[WorkflowPhase.DESIGN],
                applicable_documents=[DocumentType.DESIGN]
            ),
            ValidationRule(
                id="structure_tasks",
                name="Tasks Structure",
                description="Validate tasks document structure and format",
                type=ValidationType.STRUCTURE,
                severity=ValidationSeverity.ERROR,
                applicable_phases=[WorkflowPhase.TASKS],
                applicable_documents=[DocumentType.TASKS]
            ),
            ValidationRule(
                id="content_quality",
                name="Content Quality",
                description="Validate document content quality and completeness",
                type=ValidationType.CONTENT,
                severity=ValidationSeverity.WARNING,
                applicable_phases=list(WorkflowPhase),
                applicable_documents=list(DocumentType)
            ),
            ValidationRule(
                id="format_markdown",
                name="Markdown Format",
                description="Validate markdown formatting and syntax",
                type=ValidationType.FORMAT,
                severity=ValidationSeverity.WARNING,
                applicable_phases=list(WorkflowPhase),
                applicable_documents=list(DocumentType)
            ),
            ValidationRule(
                id="consistency_cross_document",
                name="Cross-Document Consistency",
                description="Validate consistency across multiple documents",
                type=ValidationType.CONSISTENCY,
                severity=ValidationSeverity.WARNING,
                applicable_phases=[WorkflowPhase.DESIGN, WorkflowPhase.TASKS, WorkflowPhase.EXECUTION]
            ),
            ValidationRule(
                id="consistency_single_document",
                name="Single Document Consistency",
                description="Validate consistency within a single document",
                type=ValidationType.CONSISTENCY,
                severity=ValidationSeverity.ERROR,
                applicable_phases=list(WorkflowPhase),
                applicable_documents=list(DocumentType)
            ),
            ValidationRule(
                id="traceability_requirements",
                name="Requirements Traceability",
                description="Validate requirement traceability across documents",
                type=ValidationType.TRACEABILITY,
                severity=ValidationSeverity.WARNING,
                applicable_phases=[WorkflowPhase.TASKS, WorkflowPhase.EXECUTION]
            ),
            ValidationRule(
                id="workflow_state",
                name="Workflow State",
                description="Validate workflow state and transitions",
                type=ValidationType.WORKFLOW,
                severity=ValidationSeverity.ERROR,
                applicable_phases=list(WorkflowPhase)
            )
        ]
        
        for rule in rules:
            self.rules[rule.id] = rule
    
    def _setup_validators(self) -> None:
        """Set up validator instances."""
        self.validators.update({
            "structure_requirements": StructureValidator(self.rules["structure_requirements"]),
            "structure_design": StructureValidator(self.rules["structure_design"]),
            "structure_tasks": StructureValidator(self.rules["structure_tasks"]),
            "content_quality": ContentValidator(self.rules["content_quality"]),
            "format_markdown": FormatValidator(self.rules["format_markdown"]),
            "consistency_cross_document": ConsistencyValidator(self.rules["consistency_cross_document"]),
            "consistency_single_document": ConsistencyValidator(self.rules["consistency_single_document"]),
            "traceability_requirements": TraceabilityValidator(self.rules["traceability_requirements"]),
            "workflow_state": WorkflowValidator(self.rules["workflow_state"])
        })
    
    def validate_document(
        self,
        content: str,
        document_type: DocumentType,
        phase: WorkflowPhase,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationReport:
        """Validate a single document."""
        if context is None:
            context = {}
        
        context.update({
            'document_type': document_type,
            'phase': phase
        })
        
        issues = []
        rules_checked = []
        
        for validator_id, validator in self.validators.items():
            if validator.is_applicable(phase, document_type):
                validator_issues = validator.validate(content, context)
                issues.extend(validator_issues)
                rules_checked.append(validator_id)
        
        # Generate summary
        summary = {
            'total_issues': len(issues),
            'errors': len([i for i in issues if i.severity == ValidationSeverity.ERROR]),
            'warnings': len([i for i in issues if i.severity == ValidationSeverity.WARNING]),
            'info': len([i for i in issues if i.severity == ValidationSeverity.INFO])
        }
        
        # Determine overall status
        if summary['errors'] > 0:
            overall_status = "errors"
        elif summary['warnings'] > 0:
            overall_status = "warnings"
        else:
            overall_status = "valid"
        
        return ValidationReport(
            spec_id=context.get('spec_id', 'unknown'),
            validation_time=datetime.utcnow(),
            overall_status=overall_status,
            issues=issues,
            rules_checked=rules_checked,
            summary=summary
        )
    
    def validate_spec(
        self,
        spec_id: str,
        documents: Dict[str, str],
        current_phase: WorkflowPhase,
        workflow_status: WorkflowStatus,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationReport:
        """Validate an entire spec with all its documents."""
        if context is None:
            context = {}
        
        context.update({
            'spec_id': spec_id,
            'current_phase': current_phase,
            'workflow_status': workflow_status,
            'documents': documents
        })
        
        all_issues = []
        all_rules_checked = []
        
        # Validate individual documents
        for doc_type_str, content in documents.items():
            if content:
                try:
                    doc_type = DocumentType(doc_type_str)
                    doc_context = context.copy()
                    doc_context['document_type'] = doc_type
                    
                    for validator_id, validator in self.validators.items():
                        if validator.is_applicable(current_phase, doc_type):
                            validator_issues = validator.validate(content, doc_context)
                            all_issues.extend(validator_issues)
                            if validator_id not in all_rules_checked:
                                all_rules_checked.append(validator_id)
                
                except ValueError:
                    # Unknown document type, skip
                    continue
        
        # Validate cross-document consistency and traceability
        cross_doc_context = context.copy()
        cross_doc_context['documents'] = documents
        
        for validator_id, validator in self.validators.items():
            if (validator.rule.type in [ValidationType.CONSISTENCY, ValidationType.TRACEABILITY] and
                validator.is_applicable(current_phase)):
                validator_issues = validator.validate({'documents': documents}, cross_doc_context)
                all_issues.extend(validator_issues)
                if validator_id not in all_rules_checked:
                    all_rules_checked.append(validator_id)
        
        # Validate workflow state
        workflow_validator = self.validators.get('workflow_state')
        if workflow_validator and workflow_validator.is_applicable(current_phase):
            workflow_issues = workflow_validator.validate(None, context)
            all_issues.extend(workflow_issues)
            if 'workflow_state' not in all_rules_checked:
                all_rules_checked.append('workflow_state')
        
        # Generate summary
        summary = {
            'total_issues': len(all_issues),
            'errors': len([i for i in all_issues if i.severity == ValidationSeverity.ERROR]),
            'warnings': len([i for i in all_issues if i.severity == ValidationSeverity.WARNING]),
            'info': len([i for i in all_issues if i.severity == ValidationSeverity.INFO])
        }
        
        # Determine overall status
        if summary['errors'] > 0:
            overall_status = "errors"
        elif summary['warnings'] > 0:
            overall_status = "warnings"
        else:
            overall_status = "valid"
        
        return ValidationReport(
            spec_id=spec_id,
            validation_time=datetime.utcnow(),
            overall_status=overall_status,
            issues=all_issues,
            rules_checked=all_rules_checked,
            summary=summary
        )
    
    def add_custom_rule(self, rule: ValidationRule, validator: BaseValidator) -> None:
        """Add a custom validation rule and validator."""
        self.rules[rule.id] = rule
        self.validators[rule.id] = validator
    
    def disable_rule(self, rule_id: str) -> None:
        """Disable a validation rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = False
    
    def enable_rule(self, rule_id: str) -> None:
        """Enable a validation rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = True
    
    def get_validation_guidance(self, issues: List[ValidationIssue]) -> Dict[str, List[str]]:
        """Get guidance for resolving validation issues."""
        guidance = {}
        
        for issue in issues:
            rule_id = issue.rule_id
            if rule_id not in guidance:
                guidance[rule_id] = []
            
            if issue.suggestion:
                guidance[rule_id].append(issue.suggestion)
            else:
                # Generate generic guidance based on issue type
                rule = self.rules.get(rule_id)
                if rule:
                    if rule.type == ValidationType.STRUCTURE:
                        guidance[rule_id].append("Review document structure and ensure all required sections are present")
                    elif rule.type == ValidationType.CONTENT:
                        guidance[rule_id].append("Review content quality and add missing information")
                    elif rule.type == ValidationType.FORMAT:
                        guidance[rule_id].append("Fix formatting issues according to markdown standards")
                    elif rule.type == ValidationType.CONSISTENCY:
                        guidance[rule_id].append("Review document consistency and resolve conflicts")
                    elif rule.type == ValidationType.TRACEABILITY:
                        guidance[rule_id].append("Ensure proper requirement traceability across documents")
        
        return guidance
    
    def auto_fix_issues(self, content: str, issues: List[ValidationIssue]) -> str:
        """Attempt to automatically fix validation issues where possible."""
        fixed_content = content
        
        for issue in issues:
            if issue.auto_fixable:
                # Implement auto-fixes for common issues
                if "space after #" in issue.message:
                    # Fix header spacing
                    lines = fixed_content.split('\n')
                    if issue.line_number and issue.line_number <= len(lines):
                        line = lines[issue.line_number - 1]
                        if line.startswith('#') and not line.startswith('# '):
                            fixed_line = re.sub(r'^(#+)([^\s])', r'\1 \2', line)
                            lines[issue.line_number - 1] = fixed_line
                            fixed_content = '\n'.join(lines)
        
        return fixed_content