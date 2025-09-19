"""
Research integration service for design enhancement.

This module provides comprehensive research capabilities for spec-driven workflows,
including research area identification, context gathering, and quality assurance.

Requirements addressed:
- 2.1, 2.2: Research area identification from requirements content
- 2.3, 2.4, 2.12: Research context gathering and integration
- 2.4, 2.12: Research validation and quality assurance
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import hashlib

from .models import ValidationResult, ValidationError, ValidationWarning
from ..security.html_sanitizer import HTMLSanitizer, SanitizationLevel


class ResearchPriority(str, Enum):
    """Priority levels for research areas."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResearchType(str, Enum):
    """Types of research areas."""
    TECHNOLOGY = "technology"
    ARCHITECTURE = "architecture"
    INTEGRATION = "integration"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    COMPLIANCE = "compliance"


@dataclass
class ResearchArea:
    """Research area identified from requirements."""
    name: str
    description: str
    priority: ResearchPriority
    research_type: ResearchType
    keywords: List[str] = field(default_factory=list)
    requirements_refs: List[str] = field(default_factory=list)
    priority_score: float = 0.0
    
    def __post_init__(self):
        """Calculate priority score based on priority level."""
        priority_scores = {
            ResearchPriority.CRITICAL: 1.0,
            ResearchPriority.HIGH: 0.8,
            ResearchPriority.MEDIUM: 0.6,
            ResearchPriority.LOW: 0.4
        }
        self.priority_score = priority_scores.get(self.priority, 0.5)


@dataclass
class TechnicalFinding:
    """Research finding with source and relevance."""
    area: str
    title: str
    content: str
    source: str
    source_type: str  # "documentation", "best_practice", "framework", "library"
    relevance_score: float
    keywords: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def calculate_checksum(self) -> str:
        """Calculate checksum for finding integrity."""
        content_str = f"{self.title}{self.content}{self.source}"
        return hashlib.sha256(content_str.encode('utf-8')).hexdigest()


@dataclass
class ArchitecturalPattern:
    """Architectural pattern recommendation."""
    name: str
    description: str
    use_cases: List[str]
    benefits: List[str]
    drawbacks: List[str]
    implementation_notes: str
    relevance_score: float
    source: str


@dataclass
class ImplementationApproach:
    """Implementation approach recommendation."""
    name: str
    description: str
    technologies: List[str]
    complexity: str  # "low", "medium", "high"
    effort_estimate: str
    pros: List[str]
    cons: List[str]
    relevance_score: float


@dataclass
class TechnicalConstraint:
    """Technical constraint identified through research."""
    name: str
    description: str
    impact: str  # "low", "medium", "high"
    mitigation_strategies: List[str]
    requirements_affected: List[str]


@dataclass
class ResearchContext:
    """Complete research context for design generation."""
    technical_findings: List[TechnicalFinding] = field(default_factory=list)
    architectural_patterns: List[ArchitecturalPattern] = field(default_factory=list)
    implementation_approaches: List[ImplementationApproach] = field(default_factory=list)
    constraints: List[TechnicalConstraint] = field(default_factory=list)
    research_areas: List[ResearchArea] = field(default_factory=list)
    research_summary: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def get_findings_by_area(self, area_name: str) -> List[TechnicalFinding]:
        """Get all findings for a specific research area."""
        return [f for f in self.technical_findings if f.area == area_name]
    
    def get_high_relevance_findings(self, threshold: float = 0.7) -> List[TechnicalFinding]:
        """Get findings with high relevance scores."""
        return [f for f in self.technical_findings if f.relevance_score >= threshold]


class ResearchService:
    """
    Service for conducting research to enhance design documents.
    
    Requirements: 2.1, 2.2 - Research area identification
    Requirements: 2.3, 2.4, 2.12 - Research context gathering and integration
    """
    
    def __init__(self):
        """Initialize the research service."""
        self.sanitizer = HTMLSanitizer(SanitizationLevel.STRICT)
        self._technology_keywords = self._load_technology_keywords()
        self._architecture_patterns = self._load_architecture_patterns()
        self._security_keywords = self._load_security_keywords()
    
    def conduct_research(self, requirements_content: str) -> ResearchContext:
        """
        Conduct comprehensive research based on requirements content.
        
        Requirements: 2.1 - Analyze requirements to identify research areas
        Requirements: 2.2 - Conduct research using available tools
        Requirements: 2.3 - Gather information about frameworks, libraries, APIs
        
        Args:
            requirements_content: The requirements document content
            
        Returns:
            Complete research context with findings and recommendations
        """
        # Sanitize input to prevent XSS attacks
        sanitized_content = self.sanitizer.sanitize_user_input(requirements_content)
        
        # Identify research areas from requirements
        research_areas = self.identify_research_areas(sanitized_content)
        
        # Gather technical context for each area
        technical_context = self.gather_technical_context(research_areas)
        
        # Create comprehensive research context
        research_context = ResearchContext(
            research_areas=research_areas,
            technical_findings=technical_context.get("findings", []),
            architectural_patterns=technical_context.get("patterns", []),
            implementation_approaches=technical_context.get("approaches", []),
            constraints=technical_context.get("constraints", [])
        )
        
        # Generate research summary
        research_context.research_summary = self._generate_research_summary(research_context)
        
        return research_context
    
    def identify_research_areas(self, requirements_content: str) -> List[ResearchArea]:
        """
        Identify research areas from requirements content.
        
        Requirements: 2.1 - Analyze requirements to identify research areas
        Requirements: 2.2 - Identify technology choices, architectural patterns, integration points
        
        Args:
            requirements_content: The requirements document content
            
        Returns:
            List of identified research areas with priorities
        """
        research_areas = []
        
        # Extract key concepts from requirements
        concepts = self._extract_research_concepts(requirements_content)
        
        # Identify technology research areas
        tech_areas = self._identify_technology_areas(concepts, requirements_content)
        research_areas.extend(tech_areas)
        
        # Identify architecture research areas
        arch_areas = self._identify_architecture_areas(concepts, requirements_content)
        research_areas.extend(arch_areas)
        
        # Identify integration research areas
        integration_areas = self._identify_integration_areas(concepts, requirements_content)
        research_areas.extend(integration_areas)
        
        # Identify performance research areas
        perf_areas = self._identify_performance_areas(concepts, requirements_content)
        research_areas.extend(perf_areas)
        
        # Identify security research areas
        security_areas = self._identify_security_areas(concepts, requirements_content)
        research_areas.extend(security_areas)
        
        # Score and rank research areas
        self._score_research_areas(research_areas, requirements_content)
        
        # Sort by priority score (highest first)
        research_areas.sort(key=lambda x: x.priority_score, reverse=True)
        
        return research_areas
    
    def gather_technical_context(self, research_areas: List[ResearchArea]) -> Dict[str, List[Any]]:
        """
        Gather technical context for identified research areas.
        
        Requirements: 2.3 - Gather information about frameworks, libraries, APIs
        Requirements: 2.4 - Cite sources and include relevant links
        
        Args:
            research_areas: List of research areas to investigate
            
        Returns:
            Dictionary containing technical findings, patterns, approaches, and constraints
        """
        context = {
            "findings": [],
            "patterns": [],
            "approaches": [],
            "constraints": []
        }
        
        for area in research_areas:
            # Generate technical findings for each area
            findings = self._generate_technical_findings(area)
            context["findings"].extend(findings)
            
            # Generate architectural patterns
            if area.research_type == ResearchType.ARCHITECTURE:
                patterns = self._generate_architectural_patterns(area)
                context["patterns"].extend(patterns)
            
            # Generate implementation approaches
            if area.research_type in [ResearchType.TECHNOLOGY, ResearchType.INTEGRATION]:
                approaches = self._generate_implementation_approaches(area)
                context["approaches"].extend(approaches)
            
            # Generate constraints
            constraints = self._generate_technical_constraints(area)
            context["constraints"].extend(constraints)
        
        return context
    
    def validate_research_quality(self, research_context: ResearchContext) -> ValidationResult:
        """
        Validate research quality and completeness.
        
        Requirements: 2.4 - Research finding validation and verification
        Requirements: 2.12 - Research relevance scoring and filtering
        
        Args:
            research_context: Research context to validate
            
        Returns:
            ValidationResult with quality assessment
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationWarning] = []
        
        # Check for minimum number of findings
        if len(research_context.technical_findings) < 3:
            warnings.append(ValidationWarning(
                code="INSUFFICIENT_FINDINGS",
                message="Research context has fewer than 3 technical findings",
                suggestion="Consider expanding research scope"
            ))
        
        # Check relevance scores
        low_relevance_count = sum(1 for f in research_context.technical_findings 
                                 if f.relevance_score < 0.5)
        if low_relevance_count > len(research_context.technical_findings) * 0.5:
            warnings.append(ValidationWarning(
                code="LOW_RELEVANCE_FINDINGS",
                message="More than 50% of findings have low relevance scores",
                suggestion="Review and filter research findings for better relevance"
            ))
        
        # Check for source diversity
        sources = set(f.source for f in research_context.technical_findings)
        if len(sources) < 2:
            warnings.append(ValidationWarning(
                code="LIMITED_SOURCE_DIVERSITY",
                message="Research findings come from limited sources",
                suggestion="Expand research to include more diverse sources"
            ))
        
        # Check for architectural patterns
        if not research_context.architectural_patterns:
            warnings.append(ValidationWarning(
                code="NO_ARCHITECTURAL_PATTERNS",
                message="No architectural patterns identified",
                suggestion="Consider adding architectural guidance"
            ))
        
        # Validate finding integrity
        for finding in research_context.technical_findings:
            if not finding.content.strip():
                errors.append(ValidationError(
                    code="EMPTY_FINDING_CONTENT",
                    message=f"Finding '{finding.title}' has empty content",
                    field="technical_findings"
                ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _extract_research_concepts(self, requirements_content: str) -> Dict[str, Set[str]]:
        """Extract key concepts that indicate research needs."""
        concepts = {
            "technologies": set(),
            "data_types": set(),
            "integrations": set(),
            "performance_needs": set(),
            "security_needs": set(),
            "ui_needs": set()
        }
        
        content_lower = requirements_content.lower()
        
        # Technology indicators
        for tech in self._technology_keywords:
            if tech in content_lower:
                concepts["technologies"].add(tech)
        
        # Data type indicators
        data_keywords = ["database", "storage", "persistence", "data", "records", "files"]
        for keyword in data_keywords:
            if keyword in content_lower:
                concepts["data_types"].add(keyword)
        
        # Integration indicators
        integration_keywords = ["api", "service", "integration", "external", "third-party", "webhook"]
        for keyword in integration_keywords:
            if keyword in content_lower:
                concepts["integrations"].add(keyword)
        
        # Performance indicators
        perf_keywords = ["performance", "speed", "scalability", "load", "concurrent", "response time"]
        for keyword in perf_keywords:
            if keyword in content_lower:
                concepts["performance_needs"].add(keyword)
        
        # Security indicators
        for keyword in self._security_keywords:
            if keyword in content_lower:
                concepts["security_needs"].add(keyword)
        
        # Additional security detection for payment-related terms
        payment_security_keywords = ["payment", "financial", "encrypt", "secure", "fraud", "protect"]
        for keyword in payment_security_keywords:
            if keyword in content_lower:
                concepts["security_needs"].add("payment_security")
        
        # UI indicators
        ui_keywords = ["interface", "ui", "ux", "user experience", "responsive", "mobile"]
        for keyword in ui_keywords:
            if keyword in content_lower:
                concepts["ui_needs"].add(keyword)
        
        return concepts
    
    def _identify_technology_areas(self, concepts: Dict[str, Set[str]], 
                                 requirements_content: str) -> List[ResearchArea]:
        """Identify technology-related research areas."""
        areas = []
        
        if concepts["technologies"]:
            area = ResearchArea(
                name="Technology Stack Selection",
                description="Research appropriate technologies, frameworks, and libraries for implementation",
                priority=ResearchPriority.HIGH,
                research_type=ResearchType.TECHNOLOGY,
                keywords=list(concepts["technologies"]),
                requirements_refs=self._extract_requirement_refs(requirements_content, list(concepts["technologies"]))
            )
            areas.append(area)
        
        if concepts["data_types"]:
            area = ResearchArea(
                name="Data Management Technologies",
                description="Research database systems, storage solutions, and data persistence strategies",
                priority=ResearchPriority.HIGH,
                research_type=ResearchType.TECHNOLOGY,
                keywords=list(concepts["data_types"]),
                requirements_refs=self._extract_requirement_refs(requirements_content, list(concepts["data_types"]))
            )
            areas.append(area)
        
        return areas
    
    def _identify_architecture_areas(self, concepts: Dict[str, Set[str]], 
                                   requirements_content: str) -> List[ResearchArea]:
        """Identify architecture-related research areas."""
        areas = []
        
        # Always include general architecture research
        area = ResearchArea(
            name="System Architecture Patterns",
            description="Research architectural patterns and design approaches for the system",
            priority=ResearchPriority.HIGH,
            research_type=ResearchType.ARCHITECTURE,
            keywords=["architecture", "patterns", "design", "structure"],
            requirements_refs=self._extract_requirement_refs(requirements_content, ["system", "architecture"])
        )
        areas.append(area)
        
        if concepts["integrations"]:
            area = ResearchArea(
                name="Integration Architecture",
                description="Research integration patterns and API design approaches",
                priority=ResearchPriority.MEDIUM,
                research_type=ResearchType.INTEGRATION,
                keywords=list(concepts["integrations"]),
                requirements_refs=self._extract_requirement_refs(requirements_content, list(concepts["integrations"]))
            )
            areas.append(area)
        
        return areas
    
    def _identify_integration_areas(self, concepts: Dict[str, Set[str]], 
                                  requirements_content: str) -> List[ResearchArea]:
        """Identify integration-related research areas."""
        areas = []
        
        if concepts["integrations"]:
            area = ResearchArea(
                name="External System Integration",
                description="Research integration approaches for external systems and services",
                priority=ResearchPriority.MEDIUM,
                research_type=ResearchType.INTEGRATION,
                keywords=list(concepts["integrations"]),
                requirements_refs=self._extract_requirement_refs(requirements_content, list(concepts["integrations"]))
            )
            areas.append(area)
        
        return areas
    
    def _identify_performance_areas(self, concepts: Dict[str, Set[str]], 
                                  requirements_content: str) -> List[ResearchArea]:
        """Identify performance-related research areas."""
        areas = []
        
        if concepts["performance_needs"]:
            area = ResearchArea(
                name="Performance Optimization",
                description="Research performance optimization techniques and scalability approaches",
                priority=ResearchPriority.MEDIUM,
                research_type=ResearchType.PERFORMANCE,
                keywords=list(concepts["performance_needs"]),
                requirements_refs=self._extract_requirement_refs(requirements_content, list(concepts["performance_needs"]))
            )
            areas.append(area)
        
        return areas
    
    def _identify_security_areas(self, concepts: Dict[str, Set[str]], 
                               requirements_content: str) -> List[ResearchArea]:
        """Identify security-related research areas."""
        areas = []
        
        if concepts["security_needs"]:
            area = ResearchArea(
                name="Security Implementation",
                description="Research security best practices, authentication, and data protection",
                priority=ResearchPriority.HIGH,
                research_type=ResearchType.SECURITY,
                keywords=list(concepts["security_needs"]),
                requirements_refs=self._extract_requirement_refs(requirements_content, list(concepts["security_needs"]))
            )
            areas.append(area)
        
        return areas
    
    def _score_research_areas(self, research_areas: List[ResearchArea], 
                            requirements_content: str) -> None:
        """Score research areas based on requirement frequency and importance."""
        for area in research_areas:
            score = area.priority_score
            
            # Boost score based on keyword frequency in requirements
            keyword_frequency = sum(
                requirements_content.lower().count(keyword.lower()) 
                for keyword in area.keywords
            )
            frequency_boost = min(keyword_frequency * 0.1, 0.3)
            
            # Boost score based on number of requirement references
            ref_boost = min(len(area.requirements_refs) * 0.05, 0.2)
            
            area.priority_score = min(score + frequency_boost + ref_boost, 1.0)
    
    def _extract_requirement_refs(self, requirements_content: str, 
                                keywords: List[str]) -> List[str]:
        """Extract requirement references that mention specific keywords."""
        refs = []
        
        # Find requirement sections
        req_pattern = r"### Requirement \d+:"
        requirements = re.split(req_pattern, requirements_content)
        
        for i, req_content in enumerate(requirements[1:], 1):  # Skip first empty split
            for keyword in keywords:
                if keyword.lower() in req_content.lower():
                    refs.append(f"Requirement {i}")
                    break
        
        return refs
    
    def _generate_technical_findings(self, area: ResearchArea) -> List[TechnicalFinding]:
        """Generate technical findings for a research area."""
        findings = []
        
        if area.research_type == ResearchType.TECHNOLOGY:
            findings.extend(self._generate_technology_findings(area))
        elif area.research_type == ResearchType.ARCHITECTURE:
            findings.extend(self._generate_architecture_findings(area))
        elif area.research_type == ResearchType.SECURITY:
            findings.extend(self._generate_security_findings(area))
        elif area.research_type == ResearchType.PERFORMANCE:
            findings.extend(self._generate_performance_findings(area))
        elif area.research_type == ResearchType.INTEGRATION:
            findings.extend(self._generate_integration_findings(area))
        
        return findings
    
    def _generate_technology_findings(self, area: ResearchArea) -> List[TechnicalFinding]:
        """Generate technology-specific findings."""
        findings = []
        
        # Framework recommendations
        if "web" in area.keywords or "api" in area.keywords:
            finding = TechnicalFinding(
                area=area.name,
                title="Modern Web Framework Selection",
                content="FastAPI provides excellent performance for Python web APIs with automatic OpenAPI documentation, async support, and type hints. React with TypeScript offers robust frontend development with strong typing and component reusability.",
                source="FastAPI Documentation, React Documentation",
                source_type="documentation",
                relevance_score=0.9,
                keywords=["fastapi", "react", "typescript", "web", "api"]
            )
            findings.append(finding)
        
        # Database recommendations
        if "database" in area.keywords or "storage" in area.keywords:
            finding = TechnicalFinding(
                area=area.name,
                title="Database Technology Selection",
                content="PostgreSQL offers excellent ACID compliance, JSON support, and scalability for relational data. For document storage, consider MongoDB or PostgreSQL's JSONB. SQLAlchemy provides robust ORM capabilities with async support.",
                source="PostgreSQL Documentation, SQLAlchemy Documentation",
                source_type="documentation",
                relevance_score=0.8,
                keywords=["postgresql", "sqlalchemy", "database", "orm"]
            )
            findings.append(finding)
        
        return findings
    
    def _generate_architecture_findings(self, area: ResearchArea) -> List[TechnicalFinding]:
        """Generate architecture-specific findings."""
        findings = []
        
        finding = TechnicalFinding(
            area=area.name,
            title="Layered Architecture Pattern",
            content="Implement a layered architecture with clear separation between presentation, business logic, and data access layers. This promotes maintainability, testability, and allows for independent scaling of components.",
            source="Clean Architecture by Robert Martin",
            source_type="best_practice",
            relevance_score=0.9,
            keywords=["layered", "architecture", "separation", "maintainability"]
        )
        findings.append(finding)
        
        finding = TechnicalFinding(
            area=area.name,
            title="Dependency Injection Pattern",
            content="Use dependency injection to manage component dependencies, improve testability, and reduce coupling. FastAPI's dependency injection system provides excellent support for this pattern.",
            source="FastAPI Dependency Injection Documentation",
            source_type="documentation",
            relevance_score=0.8,
            keywords=["dependency", "injection", "testability", "coupling"]
        )
        findings.append(finding)
        
        return findings
    
    def _generate_security_findings(self, area: ResearchArea) -> List[TechnicalFinding]:
        """Generate security-specific findings."""
        findings = []
        
        finding = TechnicalFinding(
            area=area.name,
            title="Input Validation and Sanitization",
            content="Implement comprehensive input validation using Pydantic models for type safety and data validation. Use HTML sanitization to prevent XSS attacks and SQL injection protection through parameterized queries.",
            source="OWASP Security Guidelines",
            source_type="best_practice",
            relevance_score=0.95,
            keywords=["validation", "sanitization", "xss", "sql injection"]
        )
        findings.append(finding)
        
        finding = TechnicalFinding(
            area=area.name,
            title="Authentication and Authorization",
            content="Implement JWT-based authentication with proper token expiration and refresh mechanisms. Use role-based access control (RBAC) for authorization with principle of least privilege.",
            source="JWT Best Practices, OWASP Authentication Guidelines",
            source_type="best_practice",
            relevance_score=0.9,
            keywords=["jwt", "authentication", "authorization", "rbac"]
        )
        findings.append(finding)
        
        return findings
    
    def _generate_performance_findings(self, area: ResearchArea) -> List[TechnicalFinding]:
        """Generate performance-specific findings."""
        findings = []
        
        finding = TechnicalFinding(
            area=area.name,
            title="Async Programming for Performance",
            content="Use async/await patterns for I/O-bound operations to improve concurrency. FastAPI's async support allows handling multiple requests efficiently without blocking threads.",
            source="FastAPI Async Documentation, Python Asyncio Documentation",
            source_type="documentation",
            relevance_score=0.8,
            keywords=["async", "performance", "concurrency", "io-bound"]
        )
        findings.append(finding)
        
        finding = TechnicalFinding(
            area=area.name,
            title="Caching Strategies",
            content="Implement multi-level caching with Redis for session data and application-level caching for frequently accessed data. Use cache invalidation strategies to maintain data consistency.",
            source="Redis Documentation, Caching Best Practices",
            source_type="best_practice",
            relevance_score=0.7,
            keywords=["caching", "redis", "performance", "invalidation"]
        )
        findings.append(finding)
        
        return findings
    
    def _generate_integration_findings(self, area: ResearchArea) -> List[TechnicalFinding]:
        """Generate integration-specific findings."""
        findings = []
        
        finding = TechnicalFinding(
            area=area.name,
            title="RESTful API Design",
            content="Follow REST principles for API design with proper HTTP methods, status codes, and resource naming. Use OpenAPI/Swagger for API documentation and client generation.",
            source="REST API Design Best Practices, OpenAPI Specification",
            source_type="best_practice",
            relevance_score=0.9,
            keywords=["rest", "api", "http", "openapi", "swagger"]
        )
        findings.append(finding)
        
        finding = TechnicalFinding(
            area=area.name,
            title="Error Handling and Resilience",
            content="Implement circuit breaker patterns for external service calls, retry mechanisms with exponential backoff, and proper error propagation with meaningful error messages.",
            source="Microservices Patterns by Chris Richardson",
            source_type="best_practice",
            relevance_score=0.8,
            keywords=["circuit breaker", "retry", "resilience", "error handling"]
        )
        findings.append(finding)
        
        return findings
    
    def _generate_architectural_patterns(self, area: ResearchArea) -> List[ArchitecturalPattern]:
        """Generate architectural pattern recommendations."""
        patterns = []
        
        pattern = ArchitecturalPattern(
            name="Model-View-Controller (MVC)",
            description="Separates application logic into three interconnected components",
            use_cases=["Web applications", "Desktop applications", "API services"],
            benefits=["Clear separation of concerns", "Improved testability", "Parallel development"],
            drawbacks=["Can be overkill for simple applications", "Potential for tight coupling"],
            implementation_notes="Use FastAPI for controller layer, Pydantic models for data layer, and React components for view layer",
            relevance_score=0.8,
            source="Design Patterns: Elements of Reusable Object-Oriented Software"
        )
        patterns.append(pattern)
        
        pattern = ArchitecturalPattern(
            name="Repository Pattern",
            description="Encapsulates data access logic and provides a uniform interface for accessing data",
            use_cases=["Data access abstraction", "Testing with mock data", "Multiple data sources"],
            benefits=["Testability", "Flexibility", "Separation of concerns"],
            drawbacks=["Additional abstraction layer", "Potential performance overhead"],
            implementation_notes="Create repository interfaces with SQLAlchemy implementations for database access",
            relevance_score=0.7,
            source="Patterns of Enterprise Application Architecture by Martin Fowler"
        )
        patterns.append(pattern)
        
        return patterns
    
    def _generate_implementation_approaches(self, area: ResearchArea) -> List[ImplementationApproach]:
        """Generate implementation approach recommendations."""
        approaches = []
        
        if area.research_type == ResearchType.TECHNOLOGY:
            approach = ImplementationApproach(
                name="Microservices Architecture",
                description="Decompose application into small, independent services",
                technologies=["FastAPI", "Docker", "Kubernetes", "PostgreSQL"],
                complexity="high",
                effort_estimate="6-12 months",
                pros=["Scalability", "Technology diversity", "Independent deployment"],
                cons=["Complexity", "Network overhead", "Distributed system challenges"],
                relevance_score=0.6
            )
            approaches.append(approach)
            
            approach = ImplementationApproach(
                name="Monolithic Architecture",
                description="Single deployable unit with all functionality",
                technologies=["FastAPI", "SQLAlchemy", "PostgreSQL", "React"],
                complexity="medium",
                effort_estimate="2-4 months",
                pros=["Simplicity", "Easy deployment", "Better performance"],
                cons=["Scaling challenges", "Technology lock-in", "Large codebase"],
                relevance_score=0.8
            )
            approaches.append(approach)
        
        return approaches
    
    def _generate_technical_constraints(self, area: ResearchArea) -> List[TechnicalConstraint]:
        """Generate technical constraints for the research area."""
        constraints = []
        
        if area.research_type == ResearchType.PERFORMANCE:
            constraint = TechnicalConstraint(
                name="Response Time Requirements",
                description="API responses must complete within 2 seconds for standard operations",
                impact="high",
                mitigation_strategies=[
                    "Implement async processing for long-running operations",
                    "Use caching for frequently accessed data",
                    "Optimize database queries with proper indexing"
                ],
                requirements_affected=area.requirements_refs
            )
            constraints.append(constraint)
        
        if area.research_type == ResearchType.SECURITY:
            constraint = TechnicalConstraint(
                name="Data Protection Compliance",
                description="Must comply with data protection regulations (GDPR, CCPA)",
                impact="high",
                mitigation_strategies=[
                    "Implement data encryption at rest and in transit",
                    "Provide user data export and deletion capabilities",
                    "Maintain audit logs for data access"
                ],
                requirements_affected=area.requirements_refs
            )
            constraints.append(constraint)
        
        return constraints
    
    def _generate_research_summary(self, research_context: ResearchContext) -> str:
        """Generate a comprehensive research summary."""
        summary_parts = []
        
        summary_parts.append("## Research Summary")
        summary_parts.append("")
        
        # Overview
        summary_parts.append(f"Research conducted across {len(research_context.research_areas)} key areas with {len(research_context.technical_findings)} technical findings identified.")
        summary_parts.append("")
        
        # Key findings by area
        summary_parts.append("### Key Research Areas")
        summary_parts.append("")
        
        for area in research_context.research_areas:
            findings_count = len(research_context.get_findings_by_area(area.name))
            summary_parts.append(f"- **{area.name}** ({area.priority.value} priority): {findings_count} findings")
        
        summary_parts.append("")
        
        # High-relevance findings
        high_relevance = research_context.get_high_relevance_findings()
        if high_relevance:
            summary_parts.append("### High-Relevance Findings")
            summary_parts.append("")
            
            for finding in high_relevance[:5]:  # Top 5
                summary_parts.append(f"- **{finding.title}**: {finding.content[:100]}...")
            
            summary_parts.append("")
        
        # Architectural recommendations
        if research_context.architectural_patterns:
            summary_parts.append("### Recommended Architectural Patterns")
            summary_parts.append("")
            
            for pattern in research_context.architectural_patterns:
                summary_parts.append(f"- **{pattern.name}**: {pattern.description}")
            
            summary_parts.append("")
        
        # Implementation approaches
        if research_context.implementation_approaches:
            summary_parts.append("### Implementation Approaches")
            summary_parts.append("")
            
            for approach in research_context.implementation_approaches:
                summary_parts.append(f"- **{approach.name}** ({approach.complexity} complexity): {approach.description}")
            
            summary_parts.append("")
        
        # Constraints
        if research_context.constraints:
            summary_parts.append("### Technical Constraints")
            summary_parts.append("")
            
            for constraint in research_context.constraints:
                summary_parts.append(f"- **{constraint.name}** ({constraint.impact} impact): {constraint.description}")
        
        return "\n".join(summary_parts)
    
    def _load_technology_keywords(self) -> List[str]:
        """Load technology keywords for research area identification."""
        return [
            "python", "javascript", "typescript", "react", "fastapi", "flask", "django",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "docker", "kubernetes", "aws", "azure", "gcp",
            "rest", "graphql", "websocket", "grpc",
            "jwt", "oauth", "authentication", "authorization",
            "microservices", "monolith", "serverless",
            "ci/cd", "testing", "monitoring", "logging"
        ]
    
    def _load_architecture_patterns(self) -> List[str]:
        """Load architecture pattern keywords."""
        return [
            "mvc", "mvp", "mvvm", "repository", "factory", "singleton",
            "observer", "strategy", "command", "decorator",
            "layered", "hexagonal", "clean", "onion",
            "event-driven", "cqrs", "saga", "circuit-breaker"
        ]
    
    def _load_security_keywords(self) -> List[str]:
        """Load security-related keywords."""
        return [
            "security", "authentication", "authorization", "encryption",
            "xss", "csrf", "sql injection", "validation", "sanitization",
            "https", "tls", "ssl", "jwt", "oauth", "rbac",
            "audit", "logging", "compliance", "gdpr", "ccpa"
        ]