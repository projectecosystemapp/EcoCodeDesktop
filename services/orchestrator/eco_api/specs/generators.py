"""
Document generation service with AI integration for spec-driven workflows.

This module provides comprehensive document generation capabilities including
requirements generation with EARS format, design document creation with research
integration, and task list generation with requirement traceability.

Requirements addressed:
- 1.3, 1.4, 1.5, 1.6: Requirements document generation with EARS format
- 2.1-2.12: Design document generation with research integration
- 3.1-3.8: Task list generation with requirement traceability
- 5.8, 5.9, 5.11, 5.12: Document update and change management
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .models import (
    DocumentType, WorkflowPhase, ValidationResult, ValidationError, ValidationWarning
)
from ..security.html_sanitizer import HTMLSanitizer, SanitizationLevel
from .research_service import ResearchService, ResearchContext


class EARSFormat(str, Enum):
    """EARS (Easy Approach to Requirements Syntax) format types."""
    WHEN_THEN = "WHEN_THEN"
    IF_THEN = "IF_THEN"
    GIVEN_WHEN_THEN = "GIVEN_WHEN_THEN"
    WHERE_THEN = "WHERE_THEN"


@dataclass
class UserStory:
    """User story structure for requirements."""
    role: str
    feature: str
    benefit: str
    
    def to_markdown(self) -> str:
        """Convert user story to markdown format."""
        # Import here to avoid circular imports
        from ..security.html_sanitizer import escape_html
        
        # Ensure all content is HTML-escaped for safety
        safe_role = escape_html(self.role)
        safe_feature = escape_html(self.feature)
        safe_benefit = escape_html(self.benefit)
        
        return f"**User Story:** As a {safe_role}, I want {safe_feature}, so that {safe_benefit}"


@dataclass
class AcceptanceCriterion:
    """Acceptance criterion in EARS format."""
    id: str
    condition: str
    action: str
    result: str
    format_type: EARSFormat
    
    def to_markdown(self) -> str:
        """Convert acceptance criterion to markdown format."""
        # Import here to avoid circular imports
        from ..security.html_sanitizer import escape_html
        
        # Ensure all content is HTML-escaped for safety
        safe_id = escape_html(self.id)
        safe_condition = escape_html(self.condition)
        safe_action = escape_html(self.action)
        safe_result = escape_html(self.result)
        
        if self.format_type == EARSFormat.WHEN_THEN:
            return f"{safe_id}. WHEN {safe_condition} THEN {safe_action} SHALL {safe_result}"
        elif self.format_type == EARSFormat.IF_THEN:
            return f"{safe_id}. IF {safe_condition} THEN {safe_action} SHALL {safe_result}"
        elif self.format_type == EARSFormat.GIVEN_WHEN_THEN:
            return f"{safe_id}. GIVEN {safe_condition} WHEN {safe_action} THEN the system SHALL {safe_result}"
        elif self.format_type == EARSFormat.WHERE_THEN:
            return f"{safe_id}. WHERE {safe_condition} THEN {safe_action} SHALL {safe_result}"
        else:
            return f"{safe_id}. {safe_condition} {safe_action} {safe_result}"


@dataclass
class Requirement:
    """Complete requirement with user story and acceptance criteria."""
    id: str
    title: str
    user_story: UserStory
    acceptance_criteria: List[AcceptanceCriterion]
    
    def to_markdown(self) -> str:
        """Convert requirement to markdown format."""
        # Import here to avoid circular imports
        from ..security.html_sanitizer import escape_html
        
        # Ensure title is HTML-escaped for safety
        safe_title = escape_html(self.title)
        
        lines = [
            f"### {safe_title}",
            "",
            self.user_story.to_markdown(),
            "",
            "#### Acceptance Criteria",
            ""
        ]
        
        for criterion in self.acceptance_criteria:
            lines.append(criterion.to_markdown())
        
        return "\n".join(lines)


@dataclass
class ResearchArea:
    """Research area identified from requirements."""
    name: str
    description: str
    priority: int
    keywords: List[str]


@dataclass
class ResearchFinding:
    """Research finding with source and relevance."""
    area: str
    content: str
    source: str
    relevance_score: float


@dataclass
class DesignSection:
    """Design document section."""
    title: str
    content: str
    subsections: Optional[List['DesignSection']] = None


@dataclass
class Task:
    """Implementation task with traceability."""
    id: str
    description: str
    details: List[str]
    requirements: List[str]
    dependencies: List[str] = None
    subtasks: List['Task'] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.subtasks is None:
            self.subtasks = []


class RequirementsGenerator:
    """
    Generates requirements documents with EARS format support.
    
    Requirements: 1.3, 1.4, 1.5, 1.6 - Requirements document generation
    """
    
    def __init__(self):
        """Initialize the requirements generator."""
        self.requirement_counter = 1
        self.criterion_counter = 1
        self.sanitizer = HTMLSanitizer(SanitizationLevel.STRICT)
    
    def generate_requirements_document(self, feature_idea: str) -> str:
        """
        Generate a complete requirements document from a feature idea.
        
        Requirements: 1.3 - Generate comprehensive user stories with role-based personas
        Requirements: 1.4 - Create acceptance criteria in EARS format
        Requirements: 1.5 - Consider edge cases, error conditions, performance, security
        Requirements: 1.6 - Include hierarchical numbering for traceability
        Requirements: 3.1, 3.2, 3.3 - HTML sanitization for XSS prevention
        
        Args:
            feature_idea: The rough feature idea to expand into requirements
            
        Returns:
            Complete requirements document in markdown format
        """
        # Sanitize user input to prevent XSS attacks
        sanitized_feature_idea = self.sanitizer.sanitize_user_input(feature_idea)
        
        # Extract key concepts from sanitized feature idea
        concepts = self._extract_key_concepts(sanitized_feature_idea)
        
        # Generate introduction
        introduction = self._generate_introduction(sanitized_feature_idea, concepts)
        
        # Generate requirements
        requirements = self._generate_requirements(sanitized_feature_idea, concepts)
        
        # Build complete document
        document_lines = [
            "# Requirements Document",
            "",
            "## Introduction",
            "",
            introduction,
            "",
            "## Requirements",
            ""
        ]
        
        for requirement in requirements:
            document_lines.append(requirement.to_markdown())
            document_lines.append("")
        
        return "\n".join(document_lines)
    
    def _extract_key_concepts(self, feature_idea: str) -> Dict[str, List[str]]:
        """
        Extract key concepts from the feature idea.
        
        Args:
            feature_idea: The feature idea text
            
        Returns:
            Dictionary of concept categories and their values
        """
        concepts = {
            "actors": [],
            "actions": [],
            "objects": [],
            "qualities": [],
            "constraints": []
        }
        
        # Simple keyword extraction (in a real implementation, this could use NLP)
        words = feature_idea.lower().split()
        
        # Common actor patterns
        actor_keywords = ["user", "admin", "developer", "customer", "client", "manager", "system"]
        for word in words:
            if word in actor_keywords:
                concepts["actors"].append(word)
        
        # Common action patterns
        action_keywords = ["create", "update", "delete", "view", "manage", "configure", "execute", "generate"]
        for word in words:
            if word in action_keywords:
                concepts["actions"].append(word)
        
        # If no specific actors found, default to "user"
        if not concepts["actors"]:
            concepts["actors"] = ["user"]
        
        # If no specific actions found, infer from feature idea
        if not concepts["actions"]:
            if "manage" in feature_idea.lower():
                concepts["actions"] = ["manage", "create", "update"]
            else:
                concepts["actions"] = ["use", "access"]
        
        return concepts
    
    def _generate_introduction(self, feature_idea: str, concepts: Dict[str, List[str]]) -> str:
        """
        Generate the introduction section for the requirements document.
        
        Args:
            feature_idea: The original feature idea
            concepts: Extracted key concepts
            
        Returns:
            Introduction text
        """
        # Create a more detailed introduction based on the feature idea
        feature_name = self._extract_feature_name(feature_idea)
        
        introduction = f"""The {feature_name} feature provides comprehensive functionality to address the core needs identified in the feature concept: "{feature_idea}". This feature implements a systematic approach to deliver the required capabilities while ensuring proper user experience, security, and system integration.

The feature is designed to serve multiple user types including {', '.join(concepts['actors'])} with capabilities for {', '.join(concepts['actions'])}. The implementation focuses on usability, reliability, and maintainability while addressing both functional and non-functional requirements including performance, security, and error handling considerations."""
        
        return introduction
    
    def _extract_feature_name(self, feature_idea: str) -> str:
        """Extract a readable feature name from the idea."""
        # Take first few words and clean them up
        words = feature_idea.split()[:4]
        return " ".join(word.capitalize() for word in words if word.isalpha())
    
    def _generate_requirements(self, feature_idea: str, concepts: Dict[str, List[str]]) -> List[Requirement]:
        """
        Generate a comprehensive list of requirements.
        
        Args:
            feature_idea: The feature idea
            concepts: Extracted key concepts
            
        Returns:
            List of Requirement objects
        """
        requirements = []
        
        # Core functional requirement
        requirements.append(self._create_core_functional_requirement(feature_idea, concepts))
        
        # User interface requirement
        requirements.append(self._create_user_interface_requirement(concepts))
        
        # Data management requirement
        requirements.append(self._create_data_management_requirement(concepts))
        
        # Security and validation requirement
        requirements.append(self._create_security_requirement(concepts))
        
        # Performance and reliability requirement
        requirements.append(self._create_performance_requirement(concepts))
        
        # Error handling requirement
        requirements.append(self._create_error_handling_requirement(concepts))
        
        # Integration requirement
        requirements.append(self._create_integration_requirement(concepts))
        
        # Workflow and state management requirement
        requirements.append(self._create_workflow_requirement(concepts))
        
        return requirements
    
    def _create_core_functional_requirement(self, feature_idea: str, concepts: Dict[str, List[str]]) -> Requirement:
        """Create the core functional requirement."""
        primary_actor = concepts["actors"][0] if concepts["actors"] else "user"
        primary_action = concepts["actions"][0] if concepts["actions"] else "use"
        
        user_story = UserStory(
            role=primary_actor,
            feature=f"{primary_action} the core functionality described in: {feature_idea}",
            benefit="I can accomplish my primary goals efficiently and effectively"
        )
        
        criteria = [
            AcceptanceCriterion(
                id="1.1",
                condition="a user initiates the primary workflow",
                action="the system",
                result="provide the core functionality as specified",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="1.2",
                condition="the core functionality is accessed",
                action="the system",
                result="respond within acceptable performance parameters",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="1.3",
                condition="invalid input is provided",
                action="the system",
                result="provide clear validation feedback",
                format_type=EARSFormat.IF_THEN
            )
        ]
        
        return Requirement(
            id="Requirement 1",
            title="Requirement 1: Core Functional Implementation",
            user_story=user_story,
            acceptance_criteria=criteria
        )
    
    def _create_user_interface_requirement(self, concepts: Dict[str, List[str]]) -> Requirement:
        """Create user interface requirement."""
        primary_actor = concepts["actors"][0] if concepts["actors"] else "user"
        
        user_story = UserStory(
            role=primary_actor,
            feature="interact with an intuitive and responsive user interface",
            benefit="I can efficiently navigate and use the feature without confusion"
        )
        
        criteria = [
            AcceptanceCriterion(
                id="2.1",
                condition="the user interface is displayed",
                action="the system",
                result="present a clear and intuitive layout",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="2.2",
                condition="user interactions occur",
                action="the system",
                result="provide immediate visual feedback",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="2.3",
                condition="the interface is accessed on different screen sizes",
                action="the system",
                result="adapt the layout appropriately",
                format_type=EARSFormat.WHEN_THEN
            )
        ]
        
        return Requirement(
            id="Requirement 2",
            title="Requirement 2: User Interface and Experience",
            user_story=user_story,
            acceptance_criteria=criteria
        )
    
    def _create_data_management_requirement(self, concepts: Dict[str, List[str]]) -> Requirement:
        """Create data management requirement."""
        primary_actor = concepts["actors"][0] if concepts["actors"] else "user"
        
        user_story = UserStory(
            role=primary_actor,
            feature="have my data managed securely and reliably",
            benefit="I can trust that my information is safe and accessible when needed"
        )
        
        criteria = [
            AcceptanceCriterion(
                id="3.1",
                condition="data is created or modified",
                action="the system",
                result="validate data integrity and format",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="3.2",
                condition="data persistence is required",
                action="the system",
                result="store data securely with appropriate encryption",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="3.3",
                condition="data retrieval is requested",
                action="the system",
                result="return accurate and up-to-date information",
                format_type=EARSFormat.WHEN_THEN
            )
        ]
        
        return Requirement(
            id="Requirement 3",
            title="Requirement 3: Data Management and Persistence",
            user_story=user_story,
            acceptance_criteria=criteria
        )
    
    def _create_security_requirement(self, concepts: Dict[str, List[str]]) -> Requirement:
        """Create security and validation requirement."""
        primary_actor = concepts["actors"][0] if concepts["actors"] else "user"
        
        user_story = UserStory(
            role=primary_actor,
            feature="have my interactions secured and validated",
            benefit="I can use the feature safely without security concerns"
        )
        
        criteria = [
            AcceptanceCriterion(
                id="4.1",
                condition="user input is received",
                action="the system",
                result="validate and sanitize all input data",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="4.2",
                condition="sensitive operations are performed",
                action="the system",
                result="require appropriate authentication and authorization",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="4.3",
                condition="security violations are detected",
                action="the system",
                result="log the incident and take protective measures",
                format_type=EARSFormat.IF_THEN
            )
        ]
        
        return Requirement(
            id="Requirement 4",
            title="Requirement 4: Security and Validation",
            user_story=user_story,
            acceptance_criteria=criteria
        )
    
    def _create_performance_requirement(self, concepts: Dict[str, List[str]]) -> Requirement:
        """Create performance and reliability requirement."""
        primary_actor = concepts["actors"][0] if concepts["actors"] else "user"
        
        user_story = UserStory(
            role=primary_actor,
            feature="experience responsive and reliable performance",
            benefit="I can work efficiently without delays or interruptions"
        )
        
        criteria = [
            AcceptanceCriterion(
                id="5.1",
                condition="operations are initiated",
                action="the system",
                result="respond within 2 seconds for standard operations",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="5.2",
                condition="system load increases",
                action="the system",
                result="maintain acceptable performance levels",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="5.3",
                condition="temporary failures occur",
                action="the system",
                result="implement retry mechanisms and graceful degradation",
                format_type=EARSFormat.IF_THEN
            )
        ]
        
        return Requirement(
            id="Requirement 5",
            title="Requirement 5: Performance and Reliability",
            user_story=user_story,
            acceptance_criteria=criteria
        )
    
    def _create_error_handling_requirement(self, concepts: Dict[str, List[str]]) -> Requirement:
        """Create error handling requirement."""
        primary_actor = concepts["actors"][0] if concepts["actors"] else "user"
        
        user_story = UserStory(
            role=primary_actor,
            feature="receive clear error messages and recovery guidance",
            benefit="I can understand and resolve issues quickly"
        )
        
        criteria = [
            AcceptanceCriterion(
                id="6.1",
                condition="errors occur during operation",
                action="the system",
                result="provide clear, actionable error messages",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="6.2",
                condition="recoverable errors are encountered",
                action="the system",
                result="suggest specific recovery actions",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="6.3",
                condition="critical errors occur",
                action="the system",
                result="log detailed information for debugging",
                format_type=EARSFormat.WHEN_THEN
            )
        ]
        
        return Requirement(
            id="Requirement 6",
            title="Requirement 6: Error Handling and Recovery",
            user_story=user_story,
            acceptance_criteria=criteria
        )
    
    def _create_integration_requirement(self, concepts: Dict[str, List[str]]) -> Requirement:
        """Create integration requirement."""
        primary_actor = concepts["actors"][0] if concepts["actors"] else "user"
        
        user_story = UserStory(
            role=primary_actor,
            feature="have the feature integrate seamlessly with existing systems",
            benefit="I can use it as part of my existing workflow without disruption"
        )
        
        criteria = [
            AcceptanceCriterion(
                id="7.1",
                condition="integration points are accessed",
                action="the system",
                result="maintain compatibility with existing interfaces",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="7.2",
                condition="data exchange occurs with external systems",
                action="the system",
                result="use standardized formats and protocols",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="7.3",
                condition="integration failures occur",
                action="the system",
                result="handle gracefully without affecting core functionality",
                format_type=EARSFormat.IF_THEN
            )
        ]
        
        return Requirement(
            id="Requirement 7",
            title="Requirement 7: System Integration",
            user_story=user_story,
            acceptance_criteria=criteria
        )
    
    def _create_workflow_requirement(self, concepts: Dict[str, List[str]]) -> Requirement:
        """Create workflow and state management requirement."""
        primary_actor = concepts["actors"][0] if concepts["actors"] else "user"
        
        user_story = UserStory(
            role=primary_actor,
            feature="have consistent workflow state management",
            benefit="I can resume work and track progress reliably"
        )
        
        criteria = [
            AcceptanceCriterion(
                id="8.1",
                condition="workflow state changes occur",
                action="the system",
                result="persist state changes immediately",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="8.2",
                condition="workflow interruptions happen",
                action="the system",
                result="allow seamless resumption from the last valid state",
                format_type=EARSFormat.WHEN_THEN
            ),
            AcceptanceCriterion(
                id="8.3",
                condition="state validation is performed",
                action="the system",
                result="ensure consistency and integrity of workflow state",
                format_type=EARSFormat.WHEN_THEN
            )
        ]
        
        return Requirement(
            id="Requirement 8",
            title="Requirement 8: Workflow and State Management",
            user_story=user_story,
            acceptance_criteria=criteria
        )
    
    def validate_requirements_format(self, content: str) -> ValidationResult:
        """
        Validate that requirements document follows proper EARS format.
        
        Args:
            content: Requirements document content
            
        Returns:
            ValidationResult with format validation details
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        # Check for required sections
        required_sections = ["# Requirements Document", "## Introduction", "## Requirements"]
        for section in required_sections:
            if section not in content:
                errors.append(ValidationError(
                    code="MISSING_SECTION",
                    message=f"Required section missing: {section}",
                    field="document_structure"
                ))
        
        # Check for user stories
        user_story_pattern = r"\*\*User Story:\*\* As a .+, I want .+, so that .+"
        user_stories = re.findall(user_story_pattern, content)
        if not user_stories:
            errors.append(ValidationError(
                code="NO_USER_STORIES",
                message="No properly formatted user stories found",
                field="user_stories"
            ))
        
        # Check for EARS format acceptance criteria
        ears_patterns = [
            r"\d+\.\d+\. WHEN .+ THEN .+ SHALL .+",
            r"\d+\.\d+\. IF .+ THEN .+ SHALL .+",
            r"\d+\.\d+\. GIVEN .+ WHEN .+ THEN .+ SHALL .+"
        ]
        
        ears_found = False
        for pattern in ears_patterns:
            if re.search(pattern, content):
                ears_found = True
                break
        
        if not ears_found:
            warnings.append(ValidationWarning(
                code="NO_EARS_FORMAT",
                message="No EARS format acceptance criteria found",
                field="acceptance_criteria",
                suggestion="Use WHEN/THEN, IF/THEN, or GIVEN/WHEN/THEN format"
            ))
        
        # Check for hierarchical numbering
        numbering_pattern = r"\d+\.\d+"
        if not re.search(numbering_pattern, content):
            warnings.append(ValidationWarning(
                code="NO_HIERARCHICAL_NUMBERING",
                message="No hierarchical numbering found in acceptance criteria",
                field="numbering",
                suggestion="Use numbered format like 1.1, 1.2, etc."
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class DesignGenerator:
    """
    Generates design documents with research integration.
    
    Requirements: 2.1, 2.2, 2.3, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11 - Design document generation
    """
    
    def __init__(self):
        """Initialize the design generator."""
        self.sanitizer = HTMLSanitizer(SanitizationLevel.STRICT)
        self.research_service = ResearchService()
    
    def generate_design_document(self, requirements_content: str, research_context: Optional[ResearchContext] = None) -> str:
        """
        Generate a complete design document from requirements with research integration.
        
        Requirements: 2.1 - Analyze requirements to identify research areas
        Requirements: 2.3 - Incorporate research findings into design
        Requirements: 2.5-2.11 - Include all mandatory design sections
        Requirements: 3.1, 3.2, 3.3 - HTML sanitization for XSS prevention
        
        Args:
            requirements_content: The requirements document content
            research_context: Optional research context to incorporate
            
        Returns:
            Complete design document in markdown format
        """
        # Sanitize requirements content to prevent XSS attacks
        sanitized_requirements_content = self.sanitizer.sanitize_user_input(requirements_content)
        
        # Parse requirements to extract key information
        requirements_info = self._parse_requirements(sanitized_requirements_content)
        
        # Conduct research if not provided
        if research_context is None:
            research_context = self.research_service.conduct_research(sanitized_requirements_content)
        
        # Generate design sections
        overview = self._generate_overview(requirements_info, research_context)
        architecture = self._generate_architecture(requirements_info, research_context)
        components = self._generate_components_and_interfaces(requirements_info, research_context)
        data_models = self._generate_data_models(requirements_info, research_context)
        error_handling = self._generate_error_handling(requirements_info, research_context)
        testing_strategy = self._generate_testing_strategy(requirements_info, research_context)
        
        # Build complete document
        document_lines = [
            "# Design Document",
            "",
            "## Overview",
            "",
            overview,
            "",
            "## Architecture",
            "",
            architecture,
            "",
            "## Components and Interfaces",
            "",
            components,
            "",
            "## Data Models",
            "",
            data_models,
            "",
            "## Error Handling",
            "",
            error_handling,
            "",
            "## Testing Strategy",
            "",
            testing_strategy
        ]
        
        return "\n".join(document_lines)
    
    def _parse_requirements(self, requirements_content: str) -> Dict[str, Any]:
        """
        Parse requirements document to extract key information.
        
        Args:
            requirements_content: Requirements document content
            
        Returns:
            Dictionary with parsed requirements information
        """
        info = {
            "feature_name": "Feature",
            "user_stories": [],
            "acceptance_criteria": [],
            "actors": set(),
            "actions": set(),
            "data_entities": set(),
            "integration_points": set()
        }
        
        # Extract feature name from introduction or title
        lines = requirements_content.split('\n')
        for line in lines:
            if line.startswith('# ') and 'Requirements' in line:
                # Try to extract feature name from title
                title_parts = line.replace('# ', '').replace(' Requirements Document', '').strip()
                if title_parts and title_parts != 'Requirements Document':
                    info["feature_name"] = title_parts
                break
        
        # Extract user stories
        user_story_pattern = r"\*\*User Story:\*\* As a (.+?), I want (.+?), so that (.+?)(?:\n|$)"
        matches = re.findall(user_story_pattern, requirements_content, re.DOTALL)
        for match in matches:
            role, feature, benefit = match
            info["user_stories"].append({
                "role": role.strip(),
                "feature": feature.strip(),
                "benefit": benefit.strip()
            })
            info["actors"].add(role.strip())
        
        # Extract acceptance criteria
        criteria_pattern = r"(\d+\.\d+)\. (WHEN|IF|GIVEN) (.+?) THEN (.+?) SHALL (.+?)(?:\n|$)"
        matches = re.findall(criteria_pattern, requirements_content, re.DOTALL)
        for match in matches:
            criterion_id, format_type, condition, action, result = match
            info["acceptance_criteria"].append({
                "id": criterion_id.strip(),
                "format": format_type.strip(),
                "condition": condition.strip(),
                "action": action.strip(),
                "result": result.strip()
            })
        
        # Extract common actions and entities
        content_lower = requirements_content.lower()
        common_actions = ["create", "update", "delete", "view", "manage", "configure", "execute", "validate", "process"]
        for action in common_actions:
            if action in content_lower:
                info["actions"].add(action)
        
        common_entities = ["user", "data", "document", "file", "record", "session", "workflow", "task", "project"]
        for entity in common_entities:
            if entity in content_lower:
                info["data_entities"].add(entity)
        
        return info
    
    def _identify_research_areas(self, requirements_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Identify research areas based on requirements analysis.
        
        Requirements: 2.1, 2.2 - Research area identification and context gathering
        
        Args:
            requirements_info: Parsed requirements information
            
        Returns:
            Research context with identified areas and findings
        """
        research_areas = []
        
        # Technology stack research
        if any(action in requirements_info["actions"] for action in ["create", "manage", "configure"]):
            research_areas.append(ResearchArea(
                name="Technology Stack",
                description="Appropriate technology choices for implementation",
                priority=1,
                keywords=["framework", "library", "database", "architecture"]
            ))
        
        # Security research
        if "security" in str(requirements_info).lower() or "authentication" in str(requirements_info).lower():
            research_areas.append(ResearchArea(
                name="Security Patterns",
                description="Security implementation patterns and best practices",
                priority=2,
                keywords=["authentication", "authorization", "encryption", "validation"]
            ))
        
        # Performance research
        if "performance" in str(requirements_info).lower() or "responsive" in str(requirements_info).lower():
            research_areas.append(ResearchArea(
                name="Performance Optimization",
                description="Performance patterns and optimization strategies",
                priority=2,
                keywords=["caching", "optimization", "scalability", "response time"]
            ))
        
        # Data management research
        if any(entity in requirements_info["data_entities"] for entity in ["data", "document", "file", "record"]):
            research_areas.append(ResearchArea(
                name="Data Management",
                description="Data storage, validation, and management patterns",
                priority=1,
                keywords=["database", "validation", "persistence", "integrity"]
            ))
        
        # Generate mock research findings (in real implementation, this would call external research services)
        findings = self._generate_mock_research_findings(research_areas)
        
        return {
            "areas": research_areas,
            "findings": findings,
            "technology_recommendations": self._generate_technology_recommendations(requirements_info),
            "architectural_patterns": self._generate_architectural_patterns(requirements_info)
        }
    
    def _generate_mock_research_findings(self, research_areas: List[ResearchArea]) -> List[ResearchFinding]:
        """Generate mock research findings for design purposes."""
        findings = []
        
        for area in research_areas:
            if area.name == "Technology Stack":
                findings.append(ResearchFinding(
                    area=area.name,
                    content="Modern web applications benefit from component-based architectures with clear separation of concerns. TypeScript provides type safety for large applications.",
                    source="Industry Best Practices",
                    relevance_score=0.9
                ))
            elif area.name == "Security Patterns":
                findings.append(ResearchFinding(
                    area=area.name,
                    content="Input validation should occur at multiple layers. Authentication tokens should be short-lived with refresh mechanisms.",
                    source="OWASP Security Guidelines",
                    relevance_score=0.95
                ))
            elif area.name == "Performance Optimization":
                findings.append(ResearchFinding(
                    area=area.name,
                    content="Response times under 2 seconds improve user satisfaction. Caching strategies should be implemented at multiple levels.",
                    source="Performance Research Studies",
                    relevance_score=0.85
                ))
            elif area.name == "Data Management":
                findings.append(ResearchFinding(
                    area=area.name,
                    content="Data integrity should be maintained through validation at input and storage layers. Checksums help detect corruption.",
                    source="Data Management Best Practices",
                    relevance_score=0.9
                ))
        
        return findings
    
    def _generate_technology_recommendations(self, requirements_info: Dict[str, Any]) -> Dict[str, str]:
        """Generate technology recommendations based on requirements."""
        return {
            "frontend": "React with TypeScript for type safety and component reusability",
            "backend": "FastAPI with Python for rapid development and automatic API documentation",
            "database": "SQLAlchemy with PostgreSQL for robust data management",
            "validation": "Pydantic for data validation and serialization",
            "testing": "pytest for backend testing, Jest for frontend testing"
        }
    
    def _generate_architectural_patterns(self, requirements_info: Dict[str, Any]) -> List[str]:
        """Generate recommended architectural patterns."""
        patterns = [
            "Layered Architecture: Separate presentation, business logic, and data layers",
            "Repository Pattern: Abstract data access logic",
            "Dependency Injection: Improve testability and modularity",
            "Observer Pattern: Handle state changes and notifications"
        ]
        
        if "workflow" in requirements_info["data_entities"]:
            patterns.append("State Machine Pattern: Manage workflow states and transitions")
        
        if len(requirements_info["actors"]) > 1:
            patterns.append("Role-Based Access Control: Manage different user permissions")
        
        return patterns
    
    def _generate_overview(self, requirements_info: Dict[str, Any], research_context: ResearchContext) -> str:
        """Generate the overview section with research integration."""
        feature_name = requirements_info["feature_name"]
        actors = list(requirements_info["actors"])
        actions = list(requirements_info["actions"])
        
        # Get high-relevance research findings for overview
        key_findings = research_context.get_high_relevance_findings(threshold=0.8)
        
        overview_parts = []
        
        overview_parts.append(f"The {feature_name} feature implements a comprehensive solution that addresses the core requirements identified in the requirements analysis. This design leverages modern architectural patterns and incorporates research findings to ensure scalability, maintainability, and user experience excellence.")
        overview_parts.append("")
        
        overview_parts.append(f"The system is designed to serve {len(actors)} primary user types: {', '.join(actors[:3])}{'...' if len(actors) > 3 else ''}, providing capabilities for {', '.join(actions[:5])}{'...' if len(actions) > 5 else ''}. The architecture emphasizes separation of concerns, type safety, and robust error handling.")
        overview_parts.append("")
        
        # Include research-informed design principles
        overview_parts.append("Key design principles include:")
        overview_parts.append("- **Modularity**: Clear separation between components with well-defined interfaces")
        overview_parts.append("- **Scalability**: Architecture supports growth in users and data volume")
        overview_parts.append("- **Security**: Multi-layer security with input validation and access controls")
        overview_parts.append("- **Reliability**: Comprehensive error handling and recovery mechanisms")
        overview_parts.append("- **Maintainability**: Clean code practices with comprehensive testing coverage")
        
        # Add research-informed insights
        if key_findings:
            overview_parts.append("")
            overview_parts.append("### Research-Informed Design Decisions")
            overview_parts.append("")
            
            for finding in key_findings[:3]:  # Top 3 findings
                overview_parts.append(f"- **{finding.title}**: {finding.content[:150]}...")
        
        overview_parts.append("")
        overview_parts.append("The implementation integrates seamlessly with existing system architecture while providing extensibility for future enhancements.")
        
        return "\n".join(overview_parts)
    
    def _generate_architecture(self, requirements_info: Dict[str, Any], research_context: ResearchContext) -> str:
        """Generate the architecture section with research integration."""
        feature_name = requirements_info["feature_name"]
        
        architecture_parts = []
        
        # System Boundaries
        architecture_parts.append("### System Boundaries")
        architecture_parts.append("")
        architecture_parts.append(f"The {feature_name} feature operates within clearly defined system boundaries:")
        architecture_parts.append("")
        architecture_parts.append("- **Presentation Layer**: User interface components and user interaction handling")
        architecture_parts.append("- **Business Logic Layer**: Core feature logic, validation, and workflow management")
        architecture_parts.append("- **Data Access Layer**: Data persistence, retrieval, and integrity management")
        architecture_parts.append("- **Integration Layer**: External system interfaces and API endpoints")
        architecture_parts.append("")
        
        # Technology Stack based on research
        architecture_parts.append("### Technology Stack")
        architecture_parts.append("")
        architecture_parts.append("Based on research findings and system requirements:")
        architecture_parts.append("")
        
        # Extract technology recommendations from research findings
        tech_findings = [f for f in research_context.technical_findings 
                        if f.area == "Technology Stack Selection" or "technology" in f.keywords]
        
        if tech_findings:
            for finding in tech_findings[:3]:  # Top 3 technology findings
                architecture_parts.append(f"- **{finding.title}**: {finding.content[:100]}...")
        else:
            architecture_parts.append("- **Frontend**: Modern web framework with TypeScript for type safety")
            architecture_parts.append("- **Backend**: Python-based API framework with async support")
            architecture_parts.append("- **Database**: Relational database with ORM for data integrity")
            architecture_parts.append("- **Validation**: Schema-based validation framework for input safety")
        
        architecture_parts.append("")
        
        # Architectural Patterns from research
        architecture_parts.append("### Architectural Patterns")
        architecture_parts.append("")
        architecture_parts.append("The design incorporates proven architectural patterns:")
        architecture_parts.append("")
        
        if research_context.architectural_patterns:
            for pattern in research_context.architectural_patterns:
                architecture_parts.append(f"- **{pattern.name}**: {pattern.description}")
                architecture_parts.append(f"  - Use cases: {', '.join(pattern.use_cases[:3])}")
                architecture_parts.append(f"  - Benefits: {', '.join(pattern.benefits[:2])}")
                architecture_parts.append("")
        else:
            architecture_parts.append("- **Layered Architecture**: Separation of concerns across presentation, business, and data layers")
            architecture_parts.append("- **Repository Pattern**: Abstraction of data access logic for testability")
            architecture_parts.append("- **Dependency Injection**: Loose coupling and improved testability")
        
        # Technical Constraints
        if research_context.constraints:
            architecture_parts.append("")
            architecture_parts.append("### Technical Constraints")
            architecture_parts.append("")
            
            for constraint in research_context.constraints:
                architecture_parts.append(f"- **{constraint.name}** ({constraint.impact} impact): {constraint.description}")
                if constraint.mitigation_strategies:
                    architecture_parts.append(f"  - Mitigation: {constraint.mitigation_strategies[0]}")
        
        return "\n".join(architecture_parts)
    
    def integrate_research_findings(self, design_content: str, research_context: ResearchContext) -> str:
        """
        Integrate research findings into existing design document.
        
        Requirements: 2.3 - Implement research findings integration into design documents
        Requirements: 2.4, 2.12 - Write research traceability and source citation management
        
        Args:
            design_content: Existing design document content
            research_context: Research context with findings to integrate
            
        Returns:
            Updated design document with integrated research findings
        """
        # Sanitize input
        sanitized_content = self.sanitizer.sanitize_user_input(design_content)
        
        # Add research findings section if not present
        if "## Research Findings" not in sanitized_content:
            research_section = self._generate_research_findings_section(research_context)
            
            # Insert before the last section (usually Testing Strategy)
            if "## Testing Strategy" in sanitized_content:
                sanitized_content = sanitized_content.replace(
                    "## Testing Strategy",
                    f"{research_section}\n\n## Testing Strategy"
                )
            else:
                sanitized_content += f"\n\n{research_section}"
        
        # Add research citations throughout the document
        sanitized_content = self._add_research_citations(sanitized_content, research_context)
        
        return sanitized_content
    
    def _generate_research_findings_section(self, research_context: ResearchContext) -> str:
        """Generate a dedicated research findings section."""
        section_parts = []
        
        section_parts.append("## Research Findings")
        section_parts.append("")
        section_parts.append("This section documents the research conducted to inform design decisions and provides traceability to sources.")
        section_parts.append("")
        
        # Group findings by area
        areas_with_findings = {}
        for finding in research_context.technical_findings:
            if finding.area not in areas_with_findings:
                areas_with_findings[finding.area] = []
            areas_with_findings[finding.area].append(finding)
        
        for area_name, findings in areas_with_findings.items():
            section_parts.append(f"### {area_name}")
            section_parts.append("")
            
            for finding in findings:
                section_parts.append(f"**{finding.title}**")
                section_parts.append("")
                section_parts.append(finding.content)
                section_parts.append("")
                section_parts.append(f"*Source: {finding.source} ({finding.source_type})*")
                section_parts.append(f"*Relevance Score: {finding.relevance_score:.2f}*")
                section_parts.append("")
        
        # Implementation approaches
        if research_context.implementation_approaches:
            section_parts.append("### Implementation Approaches")
            section_parts.append("")
            
            for approach in research_context.implementation_approaches:
                section_parts.append(f"**{approach.name}** ({approach.complexity} complexity)")
                section_parts.append("")
                section_parts.append(approach.description)
                section_parts.append("")
                section_parts.append(f"- **Technologies**: {', '.join(approach.technologies)}")
                section_parts.append(f"- **Effort Estimate**: {approach.effort_estimate}")
                section_parts.append(f"- **Pros**: {', '.join(approach.pros[:2])}")
                section_parts.append(f"- **Cons**: {', '.join(approach.cons[:2])}")
                section_parts.append("")
        
        # Research summary
        if research_context.research_summary:
            section_parts.append("### Research Summary")
            section_parts.append("")
            section_parts.append(research_context.research_summary)
        
        return "\n".join(section_parts)
    
    def _add_research_citations(self, content: str, research_context: ResearchContext) -> str:
        """Add research citations throughout the design document."""
        # Create a mapping of keywords to findings for citation
        keyword_to_findings = {}
        
        for finding in research_context.technical_findings:
            for keyword in finding.keywords:
                if keyword not in keyword_to_findings:
                    keyword_to_findings[keyword] = []
                keyword_to_findings[keyword].append(finding)
        
        # Add citations for high-relevance findings
        high_relevance_findings = research_context.get_high_relevance_findings()
        
        for finding in high_relevance_findings:
            # Look for mentions of the finding's keywords in the content
            for keyword in finding.keywords:
                if keyword.lower() in content.lower():
                    # Add a citation reference (simplified approach)
                    citation = f" [[Research: {finding.title}]]"
                    # Only add if not already present
                    if citation not in content:
                        # Find first occurrence and add citation
                        keyword_pos = content.lower().find(keyword.lower())
                        if keyword_pos != -1:
                            # Find end of sentence
                            sentence_end = content.find('.', keyword_pos)
                            if sentence_end != -1:
                                content = content[:sentence_end] + citation + content[sentence_end:]
                            break
        
        return content
        
        for i, pattern in enumerate(patterns[:5], 1):
            architecture += f"{i}. **{pattern.split(':')[0]}**: {pattern.split(':', 1)[1].strip()}\n"
        
        architecture += """
### Data Flow

```
User Input → Validation → Business Logic → Data Layer → Storage
     ↓           ↓            ↓             ↓          ↓
UI Feedback ← Error Handling ← Processing ← Retrieval ← Persistence
```

### Security Architecture

- **Input Validation**: Multi-layer validation at UI and API levels
- **Authentication**: Token-based authentication with refresh mechanisms
- **Authorization**: Role-based access control with granular permissions
- **Data Protection**: Encryption at rest and in transit"""
        
        return architecture
    
    def _generate_components_and_interfaces(self, requirements_info: Dict[str, Any], research_context: Dict[str, Any]) -> str:
        """Generate the components and interfaces section."""
        actors = list(requirements_info["actors"])
        actions = list(requirements_info["actions"])
        
        components = f"""### Core Components

#### 1. User Interface Components
- **Primary Interface**: Main user interaction component for {actors[0] if actors else 'users'}
- **Navigation Component**: Handles routing and user flow
- **Validation Component**: Real-time input validation and feedback
- **Status Component**: Progress tracking and state visualization

#### 2. Business Logic Components
- **{requirements_info["feature_name"]} Manager**: Core feature orchestration and workflow management
- **Validation Service**: Input validation and business rule enforcement
- **State Manager**: Application state management and persistence
- **Integration Service**: External system communication and data exchange

#### 3. Data Access Components
- **Repository Layer**: Abstract data access with CRUD operations
- **Model Layer**: Data models with validation and serialization
- **Cache Layer**: Performance optimization through strategic caching
- **Migration Service**: Database schema management and versioning

### Component Interfaces

#### Primary Service Interface
```typescript
interface {requirements_info["feature_name"].replace(' ', '')}Service {{
  // Core operations based on identified actions
"""
        
        for action in actions[:5]:
            components += f"  {action}Entity(data: EntityData): Promise<OperationResult>;\n"
        
        components += f"""  validateInput(input: InputData): ValidationResult;
  getStatus(): ServiceStatus;
}}
```

#### Data Repository Interface
```typescript
interface DataRepository {{
  create(entity: EntityModel): Promise<EntityModel>;
  update(id: string, data: Partial<EntityModel>): Promise<EntityModel>;
  delete(id: string): Promise<boolean>;
  findById(id: string): Promise<EntityModel | null>;
  findAll(criteria?: SearchCriteria): Promise<EntityModel[]>;
}}
```

#### Validation Interface
```typescript
interface ValidationService {{
  validateEntity(entity: EntityData): ValidationResult;
  validateBusinessRules(entity: EntityData, context: ValidationContext): ValidationResult;
  sanitizeInput(input: RawInput): SanitizedInput;
}}
```

### Integration Points

- **API Endpoints**: RESTful API for external system integration
- **Event System**: Publish/subscribe for loose coupling between components
- **Configuration Service**: Centralized configuration management
- **Logging Service**: Comprehensive logging and monitoring integration"""
        
        return components
    
    def _generate_data_models(self, requirements_info: Dict[str, Any], research_context: Dict[str, Any]) -> str:
        """Generate the data models section."""
        entities = list(requirements_info["data_entities"])
        
        data_models = f"""### Core Data Models

#### Primary Entity Model
```typescript
interface PrimaryEntity {{
  id: string;
  createdAt: Date;
  updatedAt: Date;
  version: number;
  status: EntityStatus;
  
  // Business-specific fields based on requirements
  name: string;
  description?: string;
  metadata: EntityMetadata;
}}
```

#### Validation Models
```typescript
interface ValidationResult {{
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}}

interface ValidationError {{
  field: string;
  message: string;
  code: string;
  severity: 'error' | 'warning';
}}
```

#### State Management Models
```typescript
enum EntityStatus {{
  DRAFT = 'draft',
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ARCHIVED = 'archived'
}}

interface StateTransition {{
  fromState: EntityStatus;
  toState: EntityStatus;
  timestamp: Date;
  triggeredBy: string;
  reason?: string;
}}
```

### Data Relationships

- **One-to-Many**: Primary entities can have multiple related sub-entities
- **Many-to-Many**: Cross-references between entities through junction tables
- **Hierarchical**: Parent-child relationships for nested data structures

### Data Validation Rules

1. **Required Fields**: All entities must have id, createdAt, and status
2. **Format Validation**: Specific format requirements for structured fields
3. **Business Rules**: Domain-specific validation based on requirements
4. **Referential Integrity**: Foreign key constraints and cascade rules

### Persistence Strategy

- **Primary Storage**: Relational database for structured data
- **Caching Layer**: Redis for frequently accessed data
- **File Storage**: Separate file system for large binary data
- **Backup Strategy**: Automated backups with point-in-time recovery"""
        
        return data_models
    
    def _generate_error_handling(self, requirements_info: Dict[str, Any], research_context: Dict[str, Any]) -> str:
        """Generate the error handling section."""
        error_handling = """### Error Categories

#### 1. Validation Errors
- **Input Validation**: Invalid format, missing required fields, constraint violations
- **Business Rule Violations**: Domain-specific rule failures
- **Data Integrity**: Referential integrity violations, duplicate key errors

#### 2. System Errors
- **Network Errors**: Connection timeouts, service unavailability
- **Database Errors**: Query failures, connection pool exhaustion
- **File System Errors**: Permission denied, disk space, file corruption

#### 3. Security Errors
- **Authentication Failures**: Invalid credentials, expired tokens
- **Authorization Violations**: Insufficient permissions, role violations
- **Input Security**: Injection attempts, malicious input detection

### Error Handling Strategies

#### Graceful Degradation
```typescript
interface ErrorRecoveryStrategy {
  canRecover(error: SystemError): boolean;
  recover(error: SystemError): Promise<RecoveryResult>;
  fallback(error: SystemError): FallbackResponse;
}
```

#### User-Friendly Messages
- **Technical Errors**: Translated to user-understandable messages
- **Actionable Guidance**: Specific steps users can take to resolve issues
- **Context Preservation**: Maintain user state during error recovery

#### Logging and Monitoring
- **Error Tracking**: Comprehensive error logging with context
- **Performance Monitoring**: Response time and resource usage tracking
- **Alert System**: Automated alerts for critical errors

### Recovery Mechanisms

1. **Automatic Retry**: Transient error recovery with exponential backoff
2. **Circuit Breaker**: Prevent cascade failures in distributed systems
3. **Rollback Capability**: Transaction rollback for data consistency
4. **Manual Recovery**: User-guided recovery for complex scenarios

### Error Response Format
```typescript
interface ErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: any;
    timestamp: Date;
    requestId: string;
  };
  recovery?: {
    suggestions: string[];
    retryable: boolean;
    retryAfter?: number;
  };
}
```"""
        
        return error_handling
    
    def _generate_testing_strategy(self, requirements_info: Dict[str, Any], research_context: Dict[str, Any]) -> str:
        """Generate the testing strategy section."""
        tech_recommendations = research_context.get("technology_recommendations", {})
        
        testing_strategy = f"""### Testing Approach

#### Unit Testing
- **Framework**: {tech_recommendations.get('testing', 'Jest/pytest for comprehensive unit testing')}
- **Coverage Target**: 90% code coverage for core business logic
- **Test Structure**: Arrange-Act-Assert pattern with clear test descriptions
- **Mocking Strategy**: Mock external dependencies and database interactions

#### Integration Testing
- **API Testing**: End-to-end API testing with real database interactions
- **Component Integration**: Test component interactions and data flow
- **Database Testing**: Test data persistence and retrieval operations
- **External Service Testing**: Mock external services with contract testing

#### End-to-End Testing
- **User Journey Testing**: Complete user workflows from start to finish
- **Cross-Browser Testing**: Ensure compatibility across different browsers
- **Performance Testing**: Load testing and response time validation
- **Security Testing**: Vulnerability scanning and penetration testing

### Test Data Management

#### Test Data Strategy
- **Synthetic Data**: Generated test data that covers edge cases
- **Data Fixtures**: Predefined test datasets for consistent testing
- **Data Cleanup**: Automated cleanup after test execution
- **Privacy Compliance**: No production data in test environments

#### Test Environment Management
- **Isolated Environments**: Separate test databases and services
- **Environment Parity**: Test environments mirror production configuration
- **Automated Setup**: Infrastructure as code for test environment provisioning
- **Continuous Integration**: Automated testing in CI/CD pipeline

### Quality Assurance

#### Code Quality
- **Static Analysis**: Automated code quality checks and linting
- **Code Reviews**: Peer review process for all code changes
- **Documentation**: Comprehensive code documentation and API docs
- **Performance Profiling**: Regular performance analysis and optimization

#### Acceptance Criteria Validation
Each requirement's acceptance criteria will be validated through:
- **Automated Tests**: Unit and integration tests for technical criteria
- **Manual Testing**: User experience and usability validation
- **Performance Tests**: Response time and scalability validation
- **Security Tests**: Security requirement validation

### Test Automation

#### Continuous Testing
- **Pre-commit Hooks**: Run tests before code commits
- **Build Pipeline**: Automated testing in CI/CD pipeline
- **Regression Testing**: Automated regression test suite
- **Deployment Testing**: Post-deployment smoke tests

#### Monitoring and Reporting
- **Test Results Dashboard**: Real-time test execution results
- **Coverage Reports**: Code coverage tracking and reporting
- **Performance Metrics**: Test execution time and resource usage
- **Quality Metrics**: Defect density and test effectiveness metrics"""
        
        return testing_strategy
    
    def validate_design_format(self, content: str) -> ValidationResult:
        """
        Validate that design document follows proper format and includes required sections.
        
        Args:
            content: Design document content
            
        Returns:
            ValidationResult with format validation details
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
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
                errors.append(ValidationError(
                    code="MISSING_SECTION",
                    message=f"Required section missing: {section}",
                    field="document_structure"
                ))
        
        # Check for architectural patterns
        if "architectural patterns" not in content.lower() and "architecture" in content.lower():
            warnings.append(ValidationWarning(
                code="NO_ARCHITECTURAL_PATTERNS",
                message="No architectural patterns mentioned in design",
                field="architecture",
                suggestion="Include specific architectural patterns and their rationale"
            ))
        
        # Check for technology stack
        if "technology" not in content.lower() and "stack" not in content.lower():
            warnings.append(ValidationWarning(
                code="NO_TECHNOLOGY_STACK",
                message="No technology stack specified",
                field="architecture",
                suggestion="Include specific technology choices and rationale"
            ))
        
        # Check for interfaces
        if "interface" not in content.lower():
            warnings.append(ValidationWarning(
                code="NO_INTERFACES",
                message="No component interfaces defined",
                field="components",
                suggestion="Define clear interfaces between components"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class TasksGenerator:
    """
    Generates task lists with requirement traceability and hierarchical structure.
    
    Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8 - Task list generation
    """
    
    def __init__(self):
        """Initialize the tasks generator."""
        self.task_counter = 1
        self.subtask_counter = 1
        self.sanitizer = HTMLSanitizer(SanitizationLevel.STRICT)
    
    def generate_tasks_document(self, requirements_content: str, design_content: str) -> str:
        """
        Generate a complete tasks document from requirements and design.
        
        Requirements: 3.1 - Create hierarchical numbered checkbox items
        Requirements: 3.2 - Focus exclusively on coding activities
        Requirements: 3.4 - Include clear objectives and requirement references
        Requirements: 3.5 - Ensure incremental development sequencing
        Requirements: 3.1, 3.2, 3.3 - HTML sanitization for XSS prevention
        
        Args:
            requirements_content: The requirements document content
            design_content: The design document content
            
        Returns:
            Complete tasks document in markdown format
        """
        # Sanitize input content to prevent XSS attacks
        sanitized_requirements_content = self.sanitizer.sanitize_user_input(requirements_content)
        sanitized_design_content = self.sanitizer.sanitize_user_input(design_content)
        
        # Parse requirements and design
        requirements_info = self._parse_requirements_for_tasks(sanitized_requirements_content)
        design_info = self._parse_design_for_tasks(sanitized_design_content)
        
        # Generate task hierarchy
        tasks = self._generate_task_hierarchy(requirements_info, design_info)
        
        # Build complete document
        document_lines = [
            "# Implementation Plan",
            ""
        ]
        
        for task in tasks:
            document_lines.extend(self._task_to_markdown_lines(task))
            document_lines.append("")
        
        return "\n".join(document_lines)
    
    def _parse_requirements_for_tasks(self, requirements_content: str) -> Dict[str, Any]:
        """Parse requirements document to extract task-relevant information."""
        info = {
            "requirements": [],
            "acceptance_criteria": [],
            "functional_areas": set(),
            "data_entities": set(),
            "user_interactions": set()
        }
        
        # Extract requirements with their IDs
        requirement_pattern = r"### (Requirement \d+): (.+?)\n\n\*\*User Story:\*\* (.+?)\n\n#### Acceptance Criteria\n\n(.+?)(?=\n### |$)"
        matches = re.findall(requirement_pattern, requirements_content, re.DOTALL)
        
        for match in matches:
            req_id, title, user_story, criteria_text = match
            
            # Extract acceptance criteria
            criteria = []
            criteria_pattern = r"(\d+\.\d+)\. (.+?)(?=\n\d+\.\d+|$)"
            criteria_matches = re.findall(criteria_pattern, criteria_text, re.DOTALL)
            
            for crit_match in criteria_matches:
                crit_id, crit_text = crit_match
                criteria.append({
                    "id": crit_id.strip(),
                    "text": crit_text.strip()
                })
            
            info["requirements"].append({
                "id": req_id.strip(),
                "title": title.strip(),
                "user_story": user_story.strip(),
                "criteria": criteria
            })
        
        # Extract functional areas from titles
        for req in info["requirements"]:
            title_lower = req["title"].lower()
            if "functional" in title_lower or "core" in title_lower:
                info["functional_areas"].add("core_functionality")
            elif "interface" in title_lower or "ui" in title_lower:
                info["functional_areas"].add("user_interface")
            elif "data" in title_lower or "persistence" in title_lower:
                info["functional_areas"].add("data_management")
            elif "security" in title_lower or "validation" in title_lower:
                info["functional_areas"].add("security")
            elif "performance" in title_lower:
                info["functional_areas"].add("performance")
            elif "error" in title_lower:
                info["functional_areas"].add("error_handling")
            elif "integration" in title_lower:
                info["functional_areas"].add("integration")
            elif "workflow" in title_lower or "state" in title_lower:
                info["functional_areas"].add("workflow")
        
        return info
    
    def _parse_design_for_tasks(self, design_content: str) -> Dict[str, Any]:
        """Parse design document to extract implementation-relevant information."""
        info = {
            "components": [],
            "interfaces": [],
            "data_models": [],
            "technology_stack": {},
            "architectural_patterns": []
        }
        
        # Extract components from Components and Interfaces section
        components_section = self._extract_section(design_content, "## Components and Interfaces")
        if components_section:
            # Look for component definitions
            component_pattern = r"#### (\d+\. .+?)\n(.+?)(?=\n#### |$)"
            matches = re.findall(component_pattern, components_section, re.DOTALL)
            for match in matches:
                component_name, description = match
                info["components"].append({
                    "name": component_name.strip(),
                    "description": description.strip()
                })
        
        # Extract interfaces
        interface_pattern = r"```typescript\ninterface (.+?) \{(.+?)\}\n```"
        matches = re.findall(interface_pattern, design_content, re.DOTALL)
        for match in matches:
            interface_name, interface_body = match
            info["interfaces"].append({
                "name": interface_name.strip(),
                "definition": interface_body.strip()
            })
        
        # Extract data models
        data_models_section = self._extract_section(design_content, "## Data Models")
        if data_models_section:
            model_pattern = r"#### (.+?)\n```typescript\n(.+?)\n```"
            matches = re.findall(model_pattern, data_models_section, re.DOTALL)
            for match in matches:
                model_name, model_definition = match
                info["data_models"].append({
                    "name": model_name.strip(),
                    "definition": model_definition.strip()
                })
        
        # Extract technology stack
        tech_mentions = {
            "frontend": ["react", "typescript", "javascript"],
            "backend": ["fastapi", "python", "node"],
            "database": ["postgresql", "sqlite", "mongodb"],
            "testing": ["jest", "pytest", "vitest"]
        }
        
        content_lower = design_content.lower()
        for category, keywords in tech_mentions.items():
            for keyword in keywords:
                if keyword in content_lower:
                    info["technology_stack"][category] = keyword
                    break
        
        return info
    
    def _extract_section(self, content: str, section_header: str) -> Optional[str]:
        """Extract a specific section from markdown content."""
        lines = content.split('\n')
        section_start = -1
        section_level = 0
        
        for i, line in enumerate(lines):
            if line.strip() == section_header:
                section_start = i
                section_level = len(line) - len(line.lstrip('#'))
                break
        
        if section_start == -1:
            return None
        
        section_lines = []
        for i in range(section_start + 1, len(lines)):
            line = lines[i]
            if line.startswith('#'):
                current_level = len(line) - len(line.lstrip('#'))
                if current_level <= section_level:
                    break
            section_lines.append(line)
        
        return '\n'.join(section_lines)
    
    def _generate_task_hierarchy(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> List[Task]:
        """
        Generate hierarchical task structure based on requirements and design.
        
        Requirements: 3.1 - Hierarchical task creation with maximum two levels
        Requirements: 3.5 - Ensure incremental development sequencing
        Requirements: 3.6 - Prioritize test-driven development
        """
        tasks = []
        
        # Task 1: Project Setup and Infrastructure
        tasks.append(self._create_project_setup_task(requirements_info, design_info))
        
        # Task 2: Core Data Models and Validation
        tasks.append(self._create_data_models_task(requirements_info, design_info))
        
        # Task 3: Business Logic Implementation
        tasks.append(self._create_business_logic_task(requirements_info, design_info))
        
        # Task 4: User Interface Components
        if "user_interface" in requirements_info["functional_areas"]:
            tasks.append(self._create_ui_components_task(requirements_info, design_info))
        
        # Task 5: API Endpoints and Integration
        tasks.append(self._create_api_endpoints_task(requirements_info, design_info))
        
        # Task 6: Security and Validation
        if "security" in requirements_info["functional_areas"]:
            tasks.append(self._create_security_task(requirements_info, design_info))
        
        # Task 7: Error Handling and Recovery
        if "error_handling" in requirements_info["functional_areas"]:
            tasks.append(self._create_error_handling_task(requirements_info, design_info))
        
        # Task 8: Testing and Quality Assurance
        tasks.append(self._create_testing_task(requirements_info, design_info))
        
        # Task 9: Integration and Deployment
        tasks.append(self._create_integration_task(requirements_info, design_info))
        
        return tasks
    
    def _create_project_setup_task(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> Task:
        """Create project setup and infrastructure task."""
        tech_stack = design_info.get("technology_stack", {})
        
        subtasks = [
            Task(
                id="1.1",
                description="Set up project structure and build configuration",
                details=[
                    f"Create directory structure for {tech_stack.get('frontend', 'frontend')} and {tech_stack.get('backend', 'backend')} components",
                    "Configure build tools and development environment",
                    "Set up package management and dependency configuration",
                    "Create initial configuration files and environment setup"
                ],
                requirements=["7.1", "7.2"]
            ),
            Task(
                id="1.2",
                description="Implement core type definitions and interfaces",
                details=[
                    "Define TypeScript interfaces for all major data structures",
                    "Create shared type definitions between frontend and backend",
                    "Implement validation schemas using appropriate validation library",
                    "Set up type checking and linting configuration"
                ],
                requirements=["3.1", "4.1"]
            ),
            Task(
                id="1.3",
                description="Configure development tools and testing framework",
                details=[
                    f"Set up {tech_stack.get('testing', 'testing framework')} for unit and integration testing",
                    "Configure code formatting and linting tools",
                    "Set up development server and hot reload configuration",
                    "Create initial test utilities and mock data generators"
                ],
                requirements=["8.1"]
            )
        ]
        
        return Task(
            id="1",
            description="Set up project infrastructure and core type definitions",
            details=[
                "Establish project structure with proper separation of concerns",
                "Configure build tools, testing framework, and development environment",
                "Define core interfaces and type definitions for type safety",
                "Set up development workflow and quality assurance tools"
            ],
            requirements=["7.1", "7.2", "3.1", "4.1", "8.1"],
            subtasks=subtasks
        )
    
    def _create_data_models_task(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> Task:
        """Create data models and validation task."""
        models = design_info.get("data_models", [])
        
        subtasks = [
            Task(
                id="2.1",
                description="Implement core data model classes with validation",
                details=[
                    "Create primary entity models with proper typing",
                    "Implement validation rules for all data fields",
                    "Add serialization and deserialization methods",
                    "Create model factory functions for testing"
                ],
                requirements=["3.1", "3.2", "4.1"]
            ),
            Task(
                id="2.2",
                description="Create repository pattern for data access",
                details=[
                    "Implement abstract repository interface",
                    "Create concrete repository implementations for each entity",
                    "Add CRUD operations with proper error handling",
                    "Implement query methods with filtering and pagination"
                ],
                requirements=["3.3", "7.1", "7.2"]
            ),
            Task(
                id="2.3",
                description="Add data persistence and migration support",
                details=[
                    "Set up database connection and configuration",
                    "Create database schema and migration scripts",
                    "Implement data seeding for development and testing",
                    "Add database connection pooling and optimization"
                ],
                requirements=["3.2", "3.3", "5.1", "5.2"]
            )
        ]
        
        return Task(
            id="2",
            description="Implement data models, validation, and persistence layer",
            details=[
                "Create comprehensive data models with validation and type safety",
                "Implement repository pattern for clean data access abstraction",
                "Set up database persistence with migration and seeding support",
                "Ensure data integrity and proper error handling throughout"
            ],
            requirements=["3.1", "3.2", "3.3", "4.1", "5.1", "5.2", "7.1", "7.2"],
            subtasks=subtasks
        )
    
    def _create_business_logic_task(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> Task:
        """Create business logic implementation task."""
        components = design_info.get("components", [])
        
        subtasks = [
            Task(
                id="3.1",
                description="Implement core business service classes",
                details=[
                    "Create main service classes for core functionality",
                    "Implement business rule validation and enforcement",
                    "Add workflow management and state transitions",
                    "Create service interfaces for dependency injection"
                ],
                requirements=["1.1", "1.2", "8.1", "8.2"]
            ),
            Task(
                id="3.2",
                description="Add business logic validation and processing",
                details=[
                    "Implement complex business rule validation",
                    "Create data processing and transformation logic",
                    "Add business event handling and notifications",
                    "Implement audit logging for business operations"
                ],
                requirements=["1.3", "4.1", "4.2", "6.3"]
            ),
            Task(
                id="3.3",
                description="Create workflow orchestration and state management",
                details=[
                    "Implement state machine for workflow management",
                    "Add state persistence and recovery mechanisms",
                    "Create workflow validation and transition logic",
                    "Implement progress tracking and status reporting"
                ],
                requirements=["8.1", "8.2", "8.3"]
            )
        ]
        
        return Task(
            id="3",
            description="Implement core business logic and workflow management",
            details=[
                "Create comprehensive business service layer with proper separation of concerns",
                "Implement business rule validation and complex processing logic",
                "Add workflow orchestration with state management and persistence",
                "Ensure proper error handling and audit logging throughout"
            ],
            requirements=["1.1", "1.2", "1.3", "4.1", "4.2", "6.3", "8.1", "8.2", "8.3"],
            subtasks=subtasks
        )
    
    def _create_ui_components_task(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> Task:
        """Create user interface components task."""
        tech_stack = design_info.get("technology_stack", {})
        
        subtasks = [
            Task(
                id="4.1",
                description="Create core UI component library",
                details=[
                    f"Implement reusable {tech_stack.get('frontend', 'React')} components",
                    "Create form components with validation integration",
                    "Add navigation and layout components",
                    "Implement responsive design patterns"
                ],
                requirements=["2.1", "2.2", "2.3"]
            ),
            Task(
                id="4.2",
                description="Implement user interaction and state management",
                details=[
                    "Create state management for UI components",
                    "Add user input handling and validation feedback",
                    "Implement loading states and progress indicators",
                    "Create error display and user notification components"
                ],
                requirements=["2.1", "2.2", "6.1", "6.2"]
            ),
            Task(
                id="4.3",
                description="Add accessibility and user experience features",
                details=[
                    "Implement keyboard navigation and screen reader support",
                    "Add proper ARIA labels and semantic HTML",
                    "Create responsive layouts for different screen sizes",
                    "Implement user preference and theme management"
                ],
                requirements=["2.1", "2.3"]
            )
        ]
        
        return Task(
            id="4",
            description="Implement user interface components and interactions",
            details=[
                "Create comprehensive UI component library with reusable patterns",
                "Implement user interaction handling with proper state management",
                "Add accessibility features and responsive design support",
                "Ensure proper integration with backend services and validation"
            ],
            requirements=["2.1", "2.2", "2.3", "6.1", "6.2"],
            subtasks=subtasks
        )
    
    def _create_api_endpoints_task(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> Task:
        """Create API endpoints and integration task."""
        tech_stack = design_info.get("technology_stack", {})
        
        subtasks = [
            Task(
                id="5.1",
                description="Implement RESTful API endpoints",
                details=[
                    f"Create {tech_stack.get('backend', 'FastAPI')} route handlers for all operations",
                    "Implement request/response serialization and validation",
                    "Add proper HTTP status codes and error responses",
                    "Create API documentation with OpenAPI/Swagger"
                ],
                requirements=["7.1", "7.2", "6.1", "6.2"]
            ),
            Task(
                id="5.2",
                description="Add authentication and authorization middleware",
                details=[
                    "Implement JWT token-based authentication",
                    "Create role-based authorization middleware",
                    "Add session management and token refresh logic",
                    "Implement security headers and CORS configuration"
                ],
                requirements=["4.2", "4.3"]
            ),
            Task(
                id="5.3",
                description="Create API client and service integration",
                details=[
                    "Implement frontend API client with proper error handling",
                    "Add request/response interceptors for authentication",
                    "Create service layer for API communication",
                    "Implement retry logic and offline handling"
                ],
                requirements=["7.1", "7.2", "7.3", "5.3"]
            )
        ]
        
        return Task(
            id="5",
            description="Implement API endpoints and service integration",
            details=[
                "Create comprehensive RESTful API with proper validation and documentation",
                "Implement authentication and authorization with security best practices",
                "Add frontend API client with error handling and retry mechanisms",
                "Ensure proper integration between frontend and backend services"
            ],
            requirements=["4.2", "4.3", "5.3", "6.1", "6.2", "7.1", "7.2", "7.3"],
            subtasks=subtasks
        )
    
    def _create_security_task(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> Task:
        """Create security and validation task."""
        subtasks = [
            Task(
                id="6.1",
                description="Implement input validation and sanitization",
                details=[
                    "Create comprehensive input validation for all user inputs",
                    "Add SQL injection and XSS prevention measures",
                    "Implement rate limiting and request throttling",
                    "Create input sanitization and encoding utilities"
                ],
                requirements=["4.1", "4.3"]
            ),
            Task(
                id="6.2",
                description="Add encryption and data protection",
                details=[
                    "Implement data encryption at rest and in transit",
                    "Create secure password hashing and storage",
                    "Add sensitive data masking and logging protection",
                    "Implement secure configuration management"
                ],
                requirements=["3.2", "4.2", "4.3"]
            ),
            Task(
                id="6.3",
                description="Create security monitoring and audit logging",
                details=[
                    "Implement comprehensive audit logging for security events",
                    "Add intrusion detection and anomaly monitoring",
                    "Create security incident response procedures",
                    "Implement compliance reporting and data retention policies"
                ],
                requirements=["4.3", "6.3"]
            )
        ]
        
        return Task(
            id="6",
            description="Implement security measures and data protection",
            details=[
                "Create comprehensive input validation and sanitization framework",
                "Implement encryption and secure data handling throughout the system",
                "Add security monitoring, audit logging, and incident response capabilities",
                "Ensure compliance with security best practices and regulations"
            ],
            requirements=["3.2", "4.1", "4.2", "4.3", "6.3"],
            subtasks=subtasks
        )
    
    def _create_error_handling_task(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> Task:
        """Create error handling and recovery task."""
        subtasks = [
            Task(
                id="7.1",
                description="Implement comprehensive error handling framework",
                details=[
                    "Create error classification and handling strategies",
                    "Implement global error handlers for unhandled exceptions",
                    "Add error logging with proper context and stack traces",
                    "Create error recovery and retry mechanisms"
                ],
                requirements=["6.1", "6.2", "6.3"]
            ),
            Task(
                id="7.2",
                description="Add user-friendly error messaging and recovery",
                details=[
                    "Create user-friendly error message translation system",
                    "Implement contextual help and recovery suggestions",
                    "Add error state management in UI components",
                    "Create error reporting and feedback mechanisms"
                ],
                requirements=["6.1", "6.2"]
            ),
            Task(
                id="7.3",
                description="Implement system resilience and monitoring",
                details=[
                    "Add health checks and system monitoring endpoints",
                    "Implement circuit breaker patterns for external dependencies",
                    "Create automated error alerting and notification system",
                    "Add performance monitoring and resource usage tracking"
                ],
                requirements=["5.3", "6.3"]
            )
        ]
        
        return Task(
            id="7",
            description="Implement error handling, recovery, and system resilience",
            details=[
                "Create comprehensive error handling framework with proper classification",
                "Implement user-friendly error messaging and recovery guidance",
                "Add system resilience patterns and monitoring capabilities",
                "Ensure graceful degradation and proper error reporting throughout"
            ],
            requirements=["5.3", "6.1", "6.2", "6.3"],
            subtasks=subtasks
        )
    
    def _create_testing_task(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> Task:
        """Create testing and quality assurance task."""
        tech_stack = design_info.get("technology_stack", {})
        
        subtasks = [
            Task(
                id="8.1",
                description="Implement comprehensive unit test suite",
                details=[
                    f"Create unit tests using {tech_stack.get('testing', 'Jest/pytest')} for all business logic",
                    "Add test coverage reporting and quality gates",
                    "Implement mock objects and test data factories",
                    "Create parameterized tests for edge cases and boundary conditions"
                ],
                requirements=["All requirements - unit test validation"]
            ),
            Task(
                id="8.2",
                description="Add integration and API testing",
                details=[
                    "Create integration tests for API endpoints and database operations",
                    "Implement end-to-end testing for critical user workflows",
                    "Add contract testing for external service integrations",
                    "Create performance and load testing for scalability validation"
                ],
                requirements=["All requirements - integration validation"]
            ),
            Task(
                id="8.3",
                description="Implement automated testing and quality assurance",
                details=[
                    "Set up continuous integration pipeline with automated testing",
                    "Add code quality checks and static analysis tools",
                    "Implement automated security scanning and vulnerability testing",
                    "Create test reporting and quality metrics dashboard"
                ],
                requirements=["All requirements - automated validation"]
            )
        ]
        
        return Task(
            id="8",
            description="Implement comprehensive testing and quality assurance",
            details=[
                "Create comprehensive unit test suite with high coverage and quality gates",
                "Add integration and end-to-end testing for all critical workflows",
                "Implement automated testing pipeline with continuous quality monitoring",
                "Ensure all requirements are validated through appropriate testing strategies"
            ],
            requirements=["All requirements - comprehensive testing validation"],
            subtasks=subtasks
        )
    
    def _create_integration_task(self, requirements_info: Dict[str, Any], design_info: Dict[str, Any]) -> Task:
        """Create integration and deployment task."""
        subtasks = [
            Task(
                id="9.1",
                description="Integrate all components and finalize system architecture",
                details=[
                    "Wire all components together with proper dependency injection",
                    "Implement final integration points and data flow validation",
                    "Add system-wide configuration management and environment setup",
                    "Create deployment scripts and production configuration"
                ],
                requirements=["7.1", "7.2", "7.3"]
            ),
            Task(
                id="9.2",
                description="Perform final validation and acceptance testing",
                details=[
                    "Execute complete end-to-end testing scenarios",
                    "Validate all acceptance criteria against implementation",
                    "Perform user acceptance testing and feedback incorporation",
                    "Create final documentation and user guides"
                ],
                requirements=["All requirements - final validation"]
            ),
            Task(
                id="9.3",
                description="Prepare for deployment and production readiness",
                details=[
                    "Optimize performance and resource usage for production",
                    "Implement monitoring, logging, and alerting for production environment",
                    "Create backup and disaster recovery procedures",
                    "Finalize security hardening and compliance validation"
                ],
                requirements=["5.1", "5.2", "5.3", "4.2", "4.3"]
            )
        ]
        
        return Task(
            id="9",
            description="Finalize integration, validation, and deployment preparation",
            details=[
                "Integrate all system components with proper configuration management",
                "Perform comprehensive validation against all requirements and acceptance criteria",
                "Prepare system for production deployment with monitoring and security hardening",
                "Ensure complete documentation and operational readiness"
            ],
            requirements=["4.2", "4.3", "5.1", "5.2", "5.3", "7.1", "7.2", "7.3", "All requirements - final validation"],
            subtasks=subtasks
        )
    
    def _task_to_markdown_lines(self, task: Task, indent_level: int = 0) -> List[str]:
        """
        Convert a task to markdown checkbox format.
        
        Requirements: 3.1 - Hierarchical numbered checkbox items with maximum two levels
        Requirements: 3.4 - Include clear objectives and requirement references
        """
        lines = []
        indent = "  " * indent_level
        
        # Main task line
        lines.append(f"{indent}- [ ] {task.id}. {task.description}")
        
        # Task details as sub-bullets
        for detail in task.details:
            lines.append(f"{indent}  - {detail}")
        
        # Requirements reference
        if task.requirements:
            req_text = ", ".join(task.requirements)
            lines.append(f"{indent}  - _Requirements: {req_text}_")
        
        # Subtasks (only one level deep as per requirements)
        if task.subtasks and indent_level == 0:
            for subtask in task.subtasks:
                lines.append("")
                lines.extend(self._task_to_markdown_lines(subtask, indent_level + 1))
        
        return lines
    
    def validate_tasks_format(self, content: str) -> ValidationResult:
        """
        Validate that tasks document follows proper format and coding focus.
        
        Requirements: 3.2 - Focus exclusively on coding activities
        Requirements: 3.3 - Exclude non-coding activities
        
        Args:
            content: Tasks document content
            
        Returns:
            ValidationResult with format validation details
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        # Check for required structure
        if "# Implementation Plan" not in content:
            errors.append(ValidationError(
                code="MISSING_TITLE",
                message="Tasks document must start with '# Implementation Plan'",
                field="document_structure"
            ))
        
        # Check for checkbox format
        checkbox_pattern = r"- \[ \] \d+(\.\d+)?\. .+"
        checkboxes = re.findall(checkbox_pattern, content)
        if not checkboxes:
            errors.append(ValidationError(
                code="NO_CHECKBOXES",
                message="No properly formatted checkbox tasks found",
                field="task_format"
            ))
        
        # Check for requirement references
        requirement_pattern = r"_Requirements: .+_"
        if not re.search(requirement_pattern, content):
            warnings.append(ValidationWarning(
                code="NO_REQUIREMENT_REFERENCES",
                message="No requirement references found in tasks",
                field="traceability",
                suggestion="Add requirement references to each task"
            ))
        
        # Check for non-coding activities (should not be present)
        non_coding_keywords = [
            "user testing", "user feedback", "deployment to production", 
            "performance metrics gathering", "business process", "marketing",
            "user training", "documentation creation"
        ]
        
        content_lower = content.lower()
        for keyword in non_coding_keywords:
            if keyword in content_lower:
                errors.append(ValidationError(
                    code="NON_CODING_ACTIVITY",
                    message=f"Non-coding activity found: {keyword}",
                    field="task_content"
                ))
        
        # Check for proper hierarchical numbering
        main_task_pattern = r"- \[ \] (\d+)\. "
        subtask_pattern = r"  - \[ \] (\d+\.\d+) "
        
        main_tasks = re.findall(main_task_pattern, content)
        subtasks = re.findall(subtask_pattern, content)
        
        # Validate sequential numbering
        if main_tasks:
            expected_main = list(range(1, len(main_tasks) + 1))
            actual_main = [int(task) for task in main_tasks]
            if actual_main != expected_main:
                warnings.append(ValidationWarning(
                    code="NON_SEQUENTIAL_NUMBERING",
                    message="Main task numbering is not sequential",
                    field="numbering",
                    suggestion="Use sequential numbering starting from 1"
                ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

class DocumentUpdateManager:
    """
    Manages document updates and change tracking across spec files.
    
    Requirements: 5.8, 5.9, 5.11, 5.12 - Document update and change management
    """
    
    def __init__(self):
        """Initialize the document update manager."""
        self.requirements_generator = RequirementsGenerator()
        self.design_generator = DesignGenerator()
        self.tasks_generator = TasksGenerator()
    
    def update_requirements_document(self, current_content: str, changes: Dict[str, Any]) -> Tuple[str, List[str]]:
        """
        Update requirements document with change tracking.
        
        Requirements: 5.8 - Document modification with change tracking
        Requirements: 5.9 - Document consistency validation
        
        Args:
            current_content: Current requirements document content
            changes: Dictionary of changes to apply
            
        Returns:
            Tuple of (updated_content, list_of_changes_made)
        """
        changes_made = []
        updated_content = current_content
        
        # Parse current requirements
        requirements_info = self._parse_current_requirements(current_content)
        
        # Apply changes
        if "add_requirement" in changes:
            new_req = changes["add_requirement"]
            updated_content, change_desc = self._add_requirement(updated_content, new_req, requirements_info)
            changes_made.append(change_desc)
        
        if "modify_requirement" in changes:
            mod_req = changes["modify_requirement"]
            updated_content, change_desc = self._modify_requirement(updated_content, mod_req, requirements_info)
            changes_made.append(change_desc)
        
        if "remove_requirement" in changes:
            rem_req = changes["remove_requirement"]
            updated_content, change_desc = self._remove_requirement(updated_content, rem_req, requirements_info)
            changes_made.append(change_desc)
        
        if "update_introduction" in changes:
            new_intro = changes["update_introduction"]
            updated_content, change_desc = self._update_introduction(updated_content, new_intro)
            changes_made.append(change_desc)
        
        return updated_content, changes_made
    
    def update_design_document(self, current_content: str, changes: Dict[str, Any], requirements_content: str) -> Tuple[str, List[str]]:
        """
        Update design document with consistency validation.
        
        Requirements: 5.11 - Document consistency validation across spec files
        Requirements: 5.12 - Maintain traceability during updates
        
        Args:
            current_content: Current design document content
            changes: Dictionary of changes to apply
            requirements_content: Requirements document for consistency checking
            
        Returns:
            Tuple of (updated_content, list_of_changes_made)
        """
        changes_made = []
        updated_content = current_content
        
        # Validate consistency with requirements
        consistency_issues = self._validate_design_requirements_consistency(current_content, requirements_content)
        if consistency_issues:
            changes_made.extend([f"Consistency issue detected: {issue}" for issue in consistency_issues])
        
        # Apply changes
        if "update_section" in changes:
            section_update = changes["update_section"]
            updated_content, change_desc = self._update_design_section(updated_content, section_update)
            changes_made.append(change_desc)
        
        if "add_component" in changes:
            new_component = changes["add_component"]
            updated_content, change_desc = self._add_design_component(updated_content, new_component)
            changes_made.append(change_desc)
        
        if "update_architecture" in changes:
            arch_update = changes["update_architecture"]
            updated_content, change_desc = self._update_architecture_section(updated_content, arch_update)
            changes_made.append(change_desc)
        
        return updated_content, changes_made
    
    def update_tasks_document(self, current_content: str, changes: Dict[str, Any], requirements_content: str, design_content: str) -> Tuple[str, List[str]]:
        """
        Update tasks document with requirement traceability validation.
        
        Requirements: 5.12 - Maintain requirement traceability during updates
        
        Args:
            current_content: Current tasks document content
            changes: Dictionary of changes to apply
            requirements_content: Requirements document for traceability
            design_content: Design document for consistency
            
        Returns:
            Tuple of (updated_content, list_of_changes_made)
        """
        changes_made = []
        updated_content = current_content
        
        # Validate traceability
        traceability_issues = self._validate_task_requirements_traceability(current_content, requirements_content)
        if traceability_issues:
            changes_made.extend([f"Traceability issue detected: {issue}" for issue in traceability_issues])
        
        # Apply changes
        if "add_task" in changes:
            new_task = changes["add_task"]
            updated_content, change_desc = self._add_task(updated_content, new_task)
            changes_made.append(change_desc)
        
        if "modify_task" in changes:
            mod_task = changes["modify_task"]
            updated_content, change_desc = self._modify_task(updated_content, mod_task)
            changes_made.append(change_desc)
        
        if "update_task_status" in changes:
            status_update = changes["update_task_status"]
            updated_content, change_desc = self._update_task_status(updated_content, status_update)
            changes_made.append(change_desc)
        
        return updated_content, changes_made
    
    def validate_cross_document_consistency(self, requirements_content: str, design_content: str, tasks_content: str) -> ValidationResult:
        """
        Validate consistency across all spec documents.
        
        Requirements: 5.9, 5.11 - Document consistency validation across spec files
        
        Args:
            requirements_content: Requirements document content
            design_content: Design document content
            tasks_content: Tasks document content
            
        Returns:
            ValidationResult with consistency validation details
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        # Validate requirements-design consistency
        design_issues = self._validate_design_requirements_consistency(design_content, requirements_content)
        for issue in design_issues:
            errors.append(ValidationError(
                code="DESIGN_REQUIREMENTS_INCONSISTENCY",
                message=issue,
                field="design_consistency"
            ))
        
        # Validate tasks-requirements traceability
        traceability_issues = self._validate_task_requirements_traceability(tasks_content, requirements_content)
        for issue in traceability_issues:
            errors.append(ValidationError(
                code="TASK_REQUIREMENTS_TRACEABILITY",
                message=issue,
                field="task_traceability"
            ))
        
        # Validate tasks-design consistency
        task_design_issues = self._validate_task_design_consistency(tasks_content, design_content)
        for issue in task_design_issues:
            warnings.append(ValidationWarning(
                code="TASK_DESIGN_INCONSISTENCY",
                message=issue,
                field="task_design_consistency",
                suggestion="Update tasks to align with design changes"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _parse_current_requirements(self, content: str) -> Dict[str, Any]:
        """Parse current requirements document structure."""
        info = {
            "requirements": [],
            "introduction": "",
            "requirement_count": 0
        }
        
        # Extract introduction
        intro_match = re.search(r"## Introduction\n\n(.+?)\n\n## Requirements", content, re.DOTALL)
        if intro_match:
            info["introduction"] = intro_match.group(1).strip()
        
        # Extract requirements
        req_pattern = r"### (Requirement \d+): (.+?)\n\n(.+?)(?=\n### |$)"
        matches = re.findall(req_pattern, content, re.DOTALL)
        
        for match in matches:
            req_id, title, body = match
            info["requirements"].append({
                "id": req_id.strip(),
                "title": title.strip(),
                "body": body.strip()
            })
        
        info["requirement_count"] = len(info["requirements"])
        return info
    
    def _add_requirement(self, content: str, new_requirement: Dict[str, Any], current_info: Dict[str, Any]) -> Tuple[str, str]:
        """Add a new requirement to the document."""
        req_num = current_info["requirement_count"] + 1
        req_id = f"Requirement {req_num}"
        
        # Create new requirement section
        new_req_section = f"""### {req_id}: {new_requirement['title']}

{new_requirement['user_story']}

#### Acceptance Criteria

{new_requirement['acceptance_criteria']}"""
        
        # Insert before the end of the document
        if content.endswith('\n'):
            updated_content = content + new_req_section + '\n'
        else:
            updated_content = content + '\n\n' + new_req_section + '\n'
        
        return updated_content, f"Added {req_id}: {new_requirement['title']}"
    
    def _modify_requirement(self, content: str, modification: Dict[str, Any], current_info: Dict[str, Any]) -> Tuple[str, str]:
        """Modify an existing requirement."""
        req_id = modification["requirement_id"]
        
        # Find and replace the requirement section
        req_pattern = f"### ({req_id}): (.+?)\n\n(.+?)(?=\n### |$)"
        match = re.search(req_pattern, content, re.DOTALL)
        
        if not match:
            return content, f"Requirement {req_id} not found for modification"
        
        old_section = match.group(0)
        
        # Build new section
        new_title = modification.get("title", match.group(2))
        new_body = modification.get("body", match.group(3))
        
        new_section = f"### {req_id}: {new_title}\n\n{new_body}"
        
        updated_content = content.replace(old_section, new_section)
        return updated_content, f"Modified {req_id}: {new_title}"
    
    def _remove_requirement(self, content: str, req_id: str, current_info: Dict[str, Any]) -> Tuple[str, str]:
        """Remove a requirement from the document."""
        req_pattern = f"### ({req_id}): (.+?)\n\n(.+?)(?=\n### |$)"
        match = re.search(req_pattern, content, re.DOTALL)
        
        if not match:
            return content, f"Requirement {req_id} not found for removal"
        
        section_to_remove = match.group(0)
        updated_content = content.replace(section_to_remove, "")
        
        # Clean up extra newlines
        updated_content = re.sub(r'\n{3,}', '\n\n', updated_content)
        
        return updated_content, f"Removed {req_id}"
    
    def _update_introduction(self, content: str, new_introduction: str) -> Tuple[str, str]:
        """Update the introduction section."""
        intro_pattern = r"(## Introduction\n\n)(.+?)(\n\n## Requirements)"
        match = re.search(intro_pattern, content, re.DOTALL)
        
        if not match:
            return content, "Introduction section not found"
        
        updated_content = content.replace(match.group(2), new_introduction)
        return updated_content, "Updated introduction section"
    
    def _update_design_section(self, content: str, section_update: Dict[str, Any]) -> Tuple[str, str]:
        """Update a specific section in the design document."""
        section_name = section_update["section"]
        new_content = section_update["content"]
        
        section_pattern = f"(## {section_name}\n\n)(.+?)(?=\n## |$)"
        match = re.search(section_pattern, content, re.DOTALL)
        
        if not match:
            return content, f"Section '{section_name}' not found"
        
        updated_content = content.replace(match.group(2), new_content)
        return updated_content, f"Updated {section_name} section"
    
    def _add_design_component(self, content: str, new_component: Dict[str, Any]) -> Tuple[str, str]:
        """Add a new component to the design document."""
        component_section = f"""#### {new_component['name']}
{new_component['description']}

"""
        
        # Insert in Components and Interfaces section
        components_pattern = r"(## Components and Interfaces\n\n)(.+?)(?=\n## |$)"
        match = re.search(components_pattern, content, re.DOTALL)
        
        if match:
            existing_content = match.group(2)
            new_content = existing_content + component_section
            updated_content = content.replace(match.group(2), new_content)
            return updated_content, f"Added component: {new_component['name']}"
        
        return content, "Components and Interfaces section not found"
    
    def _update_architecture_section(self, content: str, arch_update: Dict[str, Any]) -> Tuple[str, str]:
        """Update the architecture section."""
        return self._update_design_section(content, {"section": "Architecture", "content": arch_update["content"]})
    
    def _add_task(self, content: str, new_task: Dict[str, Any]) -> Tuple[str, str]:
        """Add a new task to the tasks document."""
        task_line = f"- [ ] {new_task['id']}. {new_task['description']}"
        
        # Add task details
        task_section = [task_line]
        for detail in new_task.get("details", []):
            task_section.append(f"  - {detail}")
        
        if new_task.get("requirements"):
            req_text = ", ".join(new_task["requirements"])
            task_section.append(f"  - _Requirements: {req_text}_")
        
        task_content = "\n".join(task_section) + "\n\n"
        
        # Append to the end
        updated_content = content + task_content
        return updated_content, f"Added task: {new_task['id']} - {new_task['description']}"
    
    def _modify_task(self, content: str, mod_task: Dict[str, Any]) -> Tuple[str, str]:
        """Modify an existing task."""
        task_id = mod_task["task_id"]
        
        # Find the task
        task_pattern = f"- \\[ \\] {re.escape(task_id)}\\. (.+?)(?=\n- \\[ \\]|$)"
        match = re.search(task_pattern, content, re.DOTALL)
        
        if not match:
            return content, f"Task {task_id} not found for modification"
        
        old_task = match.group(0)
        
        # Build new task
        new_description = mod_task.get("description", match.group(1).split('\n')[0])
        new_task_line = f"- [ ] {task_id}. {new_description}"
        
        # Add details if provided
        task_lines = [new_task_line]
        if mod_task.get("details"):
            for detail in mod_task["details"]:
                task_lines.append(f"  - {detail}")
        
        if mod_task.get("requirements"):
            req_text = ", ".join(mod_task["requirements"])
            task_lines.append(f"  - _Requirements: {req_text}_")
        
        new_task = "\n".join(task_lines)
        updated_content = content.replace(old_task, new_task)
        
        return updated_content, f"Modified task: {task_id}"
    
    def _update_task_status(self, content: str, status_update: Dict[str, Any]) -> Tuple[str, str]:
        """Update task completion status."""
        task_id = status_update["task_id"]
        completed = status_update["completed"]
        
        # Find and update checkbox
        if completed:
            # Change [ ] to [x]
            pattern = f"- \\[ \\] ({re.escape(task_id)}\\. .+)"
            replacement = f"- [x] \\1"
        else:
            # Change [x] to [ ]
            pattern = f"- \\[x\\] ({re.escape(task_id)}\\. .+)"
            replacement = f"- [ ] \\1"
        
        updated_content = re.sub(pattern, replacement, content)
        
        status_text = "completed" if completed else "not completed"
        return updated_content, f"Updated task {task_id} status to {status_text}"
    
    def _validate_design_requirements_consistency(self, design_content: str, requirements_content: str) -> List[str]:
        """Validate that design addresses all requirements."""
        issues = []
        
        # Extract requirement IDs from requirements document
        req_pattern = r"### (Requirement \d+):"
        requirements = re.findall(req_pattern, requirements_content)
        
        # Check if design mentions each requirement area
        design_lower = design_content.lower()
        
        for req in requirements:
            req_num = req.split()[-1]
            # This is a simplified check - in practice, would be more sophisticated
            if req_num not in design_content and req.lower() not in design_lower:
                issues.append(f"Design does not address {req}")
        
        return issues
    
    def _validate_task_requirements_traceability(self, tasks_content: str, requirements_content: str) -> List[str]:
        """Validate that tasks trace back to requirements."""
        issues = []
        
        # Extract requirement IDs from requirements
        req_pattern = r"(\d+\.\d+)\."
        requirement_ids = set(re.findall(req_pattern, requirements_content))
        
        # Extract requirement references from tasks
        task_req_pattern = r"_Requirements: (.+?)_"
        task_references = re.findall(task_req_pattern, tasks_content)
        
        referenced_ids = set()
        for ref_line in task_references:
            ids = [id.strip() for id in ref_line.split(',')]
            referenced_ids.update(ids)
        
        # Check for unreferenced requirements
        unreferenced = requirement_ids - referenced_ids
        for req_id in unreferenced:
            if req_id != "All requirements":  # Skip meta-references
                issues.append(f"Requirement {req_id} is not referenced in any task")
        
        # Check for invalid references
        invalid_refs = referenced_ids - requirement_ids
        for ref in invalid_refs:
            if not ref.startswith("All requirements"):  # Skip meta-references
                issues.append(f"Task references invalid requirement: {ref}")
        
        return issues
    
    def _validate_task_design_consistency(self, tasks_content: str, design_content: str) -> List[str]:
        """Validate that tasks align with design components."""
        issues = []
        
        # Extract components from design
        component_pattern = r"#### (.+?)\n"
        design_components = re.findall(component_pattern, design_content)
        
        # Extract technology mentions from design
        tech_pattern = r"(React|TypeScript|FastAPI|Python|PostgreSQL|SQLAlchemy)"
        design_tech = set(re.findall(tech_pattern, design_content, re.IGNORECASE))
        
        # Check if tasks mention design components or technologies
        tasks_lower = tasks_content.lower()
        design_lower = design_content.lower()
        
        # This is a simplified consistency check
        if design_tech:
            mentioned_tech = set()
            for tech in design_tech:
                if tech.lower() in tasks_lower:
                    mentioned_tech.add(tech)
            
            if len(mentioned_tech) < len(design_tech) / 2:
                issues.append("Tasks do not adequately reference design technology choices")
        
        return issues