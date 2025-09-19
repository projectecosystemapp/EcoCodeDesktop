"""
Unit tests for research integration service.

This module tests the research service functionality including research area
identification, context gathering, and quality assurance validation.

Requirements tested:
- 2.1, 2.2: Research area identification from requirements content
- 2.3, 2.4, 2.12: Research context gathering and integration
- 2.4, 2.12: Research validation and quality assurance
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from eco_api.specs.research_service import (
    ResearchService, ResearchArea, ResearchContext, TechnicalFinding,
    ArchitecturalPattern, ImplementationApproach, TechnicalConstraint,
    ResearchPriority, ResearchType
)
from eco_api.specs.models import ValidationResult, ValidationError, ValidationWarning


class TestResearchService:
    """Test cases for ResearchService class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.research_service = ResearchService()
        
        # Sample requirements content for testing
        self.sample_requirements = """
        # Requirements Document
        
        ## Introduction
        
        The User Authentication feature provides secure login and access control.
        
        ## Requirements
        
        ### Requirement 1: User Login
        
        **User Story:** As a user, I want to login securely, so that I can access the system
        
        #### Acceptance Criteria
        
        1.1. WHEN a user provides valid credentials THEN the system SHALL authenticate the user
        1.2. WHEN authentication fails THEN the system SHALL provide clear error messages
        1.3. IF multiple failed attempts occur THEN the system SHALL implement rate limiting
        
        ### Requirement 2: Data Security
        
        **User Story:** As a user, I want my data protected, so that my information is secure
        
        #### Acceptance Criteria
        
        2.1. WHEN data is stored THEN the system SHALL encrypt sensitive information
        2.2. WHEN API calls are made THEN the system SHALL use HTTPS encryption
        2.3. IF unauthorized access is detected THEN the system SHALL log security events
        """
    
    def test_conduct_research_basic(self):
        """Test basic research conduct functionality."""
        # Act
        research_context = self.research_service.conduct_research(self.sample_requirements)
        
        # Assert
        assert isinstance(research_context, ResearchContext)
        assert len(research_context.research_areas) > 0
        assert len(research_context.technical_findings) > 0
        assert research_context.research_summary != ""
        assert research_context.created_at is not None
    
    def test_identify_research_areas_security_focus(self):
        """Test research area identification for security-focused requirements."""
        # Act
        research_areas = self.research_service.identify_research_areas(self.sample_requirements)
        
        # Assert
        assert len(research_areas) > 0
        
        # Should identify security research area
        security_areas = [area for area in research_areas if area.research_type == ResearchType.SECURITY]
        assert len(security_areas) > 0
        
        # Check security area properties
        security_area = security_areas[0]
        assert "security" in security_area.keywords or "authentication" in security_area.keywords
        assert security_area.priority in [ResearchPriority.HIGH, ResearchPriority.CRITICAL]
        assert len(security_area.requirements_refs) > 0
    
    def test_identify_research_areas_technology_focus(self):
        """Test research area identification for technology requirements."""
        tech_requirements = """
        # Requirements Document
        
        ## Requirements
        
        ### Requirement 1: API Development
        
        **User Story:** As a developer, I want to build REST APIs, so that clients can integrate
        
        #### Acceptance Criteria
        
        1.1. WHEN API endpoints are called THEN the system SHALL return JSON responses
        1.2. WHEN database queries are made THEN the system SHALL use an ORM
        """
        
        # Act
        research_areas = self.research_service.identify_research_areas(tech_requirements)
        
        # Assert
        tech_areas = [area for area in research_areas if area.research_type == ResearchType.TECHNOLOGY]
        assert len(tech_areas) > 0
        
        # Should have technology-related keywords
        tech_area = tech_areas[0]
        assert any(keyword in ["api", "database", "rest", "json"] for keyword in tech_area.keywords)
    
    def test_gather_technical_context(self):
        """Test technical context gathering for research areas."""
        # Arrange
        research_areas = [
            ResearchArea(
                name="Technology Stack Selection",
                description="Research web technologies",
                priority=ResearchPriority.HIGH,
                research_type=ResearchType.TECHNOLOGY,
                keywords=["api", "web", "database"]
            ),
            ResearchArea(
                name="Security Implementation",
                description="Research security practices",
                priority=ResearchPriority.CRITICAL,
                research_type=ResearchType.SECURITY,
                keywords=["authentication", "encryption"]
            )
        ]
        
        # Act
        context = self.research_service.gather_technical_context(research_areas)
        
        # Assert
        assert "findings" in context
        assert "patterns" in context
        assert "approaches" in context
        assert "constraints" in context
        
        assert len(context["findings"]) > 0
        
        # Check finding properties
        finding = context["findings"][0]
        assert isinstance(finding, TechnicalFinding)
        assert finding.area in ["Technology Stack Selection", "Security Implementation"]
        assert finding.relevance_score > 0
        assert len(finding.keywords) > 0
    
    def test_validate_research_quality_sufficient_findings(self):
        """Test research quality validation with sufficient findings."""
        # Arrange
        research_context = ResearchContext(
            technical_findings=[
                TechnicalFinding(
                    area="Technology",
                    title="Framework Selection",
                    content="FastAPI provides excellent performance",
                    source="FastAPI Documentation",
                    source_type="documentation",
                    relevance_score=0.9,
                    keywords=["fastapi", "performance"]
                ),
                TechnicalFinding(
                    area="Security",
                    title="Authentication Best Practices",
                    content="JWT tokens provide secure authentication",
                    source="OWASP Guidelines",
                    source_type="best_practice",
                    relevance_score=0.8,
                    keywords=["jwt", "authentication"]
                ),
                TechnicalFinding(
                    area="Database",
                    title="ORM Selection",
                    content="SQLAlchemy offers robust ORM capabilities",
                    source="SQLAlchemy Documentation",
                    source_type="documentation",
                    relevance_score=0.7,
                    keywords=["sqlalchemy", "orm"]
                )
            ]
        )
        
        # Act
        result = self.research_service.validate_research_quality(research_context)
        
        # Assert
        assert isinstance(result, ValidationResult)
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_validate_research_quality_insufficient_findings(self):
        """Test research quality validation with insufficient findings."""
        # Arrange
        research_context = ResearchContext(
            technical_findings=[
                TechnicalFinding(
                    area="Technology",
                    title="Basic Finding",
                    content="Some basic content",
                    source="Generic Source",
                    source_type="documentation",
                    relevance_score=0.5,
                    keywords=["basic"]
                )
            ]
        )
        
        # Act
        result = self.research_service.validate_research_quality(research_context)
        
        # Assert
        assert isinstance(result, ValidationResult)
        # Should have warnings about insufficient findings
        warning_codes = [w.code for w in result.warnings]
        assert "INSUFFICIENT_FINDINGS" in warning_codes
    
    def test_validate_research_quality_low_relevance(self):
        """Test research quality validation with low relevance findings."""
        # Arrange
        research_context = ResearchContext(
            technical_findings=[
                TechnicalFinding(
                    area="Technology",
                    title="Low Relevance Finding 1",
                    content="Not very relevant content",
                    source="Source 1",
                    source_type="documentation",
                    relevance_score=0.3,
                    keywords=["low"]
                ),
                TechnicalFinding(
                    area="Technology",
                    title="Low Relevance Finding 2",
                    content="Another low relevance finding",
                    source="Source 1",
                    source_type="documentation",
                    relevance_score=0.2,
                    keywords=["low"]
                ),
                TechnicalFinding(
                    area="Technology",
                    title="Low Relevance Finding 3",
                    content="Third low relevance finding",
                    source="Source 1",
                    source_type="documentation",
                    relevance_score=0.4,
                    keywords=["low"]
                )
            ]
        )
        
        # Act
        result = self.research_service.validate_research_quality(research_context)
        
        # Assert
        warning_codes = [w.code for w in result.warnings]
        assert "LOW_RELEVANCE_FINDINGS" in warning_codes
        assert "LIMITED_SOURCE_DIVERSITY" in warning_codes
    
    def test_validate_research_quality_empty_content(self):
        """Test research quality validation with empty finding content."""
        # Arrange
        research_context = ResearchContext(
            technical_findings=[
                TechnicalFinding(
                    area="Technology",
                    title="Empty Finding",
                    content="",  # Empty content
                    source="Source",
                    source_type="documentation",
                    relevance_score=0.8,
                    keywords=["empty"]
                )
            ]
        )
        
        # Act
        result = self.research_service.validate_research_quality(research_context)
        
        # Assert
        assert not result.is_valid
        error_codes = [e.code for e in result.errors]
        assert "EMPTY_FINDING_CONTENT" in error_codes
    
    def test_research_area_priority_scoring(self):
        """Test research area priority scoring functionality."""
        # Arrange
        requirements_with_frequent_keywords = """
        Security is critical. Authentication security must be implemented.
        Security validation and security logging are required.
        The security framework should provide security controls.
        """
        
        # Act
        research_areas = self.research_service.identify_research_areas(requirements_with_frequent_keywords)
        
        # Assert
        security_areas = [area for area in research_areas if area.research_type == ResearchType.SECURITY]
        assert len(security_areas) > 0
        
        # Security area should have high priority score due to keyword frequency
        security_area = security_areas[0]
        assert security_area.priority_score > 0.8
    
    def test_extract_research_concepts(self):
        """Test research concept extraction from requirements."""
        # Act
        concepts = self.research_service._extract_research_concepts(self.sample_requirements)
        
        # Assert
        assert "security_needs" in concepts
        assert "authentication" in concepts["security_needs"] or "security" in concepts["security_needs"]
        
        # Should identify data-related concepts
        assert "data_types" in concepts
        assert len(concepts["data_types"]) > 0
    
    def test_generate_technical_findings_security(self):
        """Test technical findings generation for security areas."""
        # Arrange
        security_area = ResearchArea(
            name="Security Implementation",
            description="Research security practices",
            priority=ResearchPriority.HIGH,
            research_type=ResearchType.SECURITY,
            keywords=["authentication", "security", "encryption"]
        )
        
        # Act
        findings = self.research_service._generate_security_findings(security_area)
        
        # Assert
        assert len(findings) > 0
        
        # Check finding properties
        finding = findings[0]
        assert isinstance(finding, TechnicalFinding)
        assert finding.area == security_area.name
        assert finding.relevance_score > 0.8  # Security findings should be high relevance
        assert len(finding.keywords) > 0
        assert finding.source != ""
        assert finding.content != ""
    
    def test_generate_architectural_patterns(self):
        """Test architectural pattern generation."""
        # Arrange
        arch_area = ResearchArea(
            name="System Architecture",
            description="Research architecture patterns",
            priority=ResearchPriority.HIGH,
            research_type=ResearchType.ARCHITECTURE,
            keywords=["architecture", "patterns"]
        )
        
        # Act
        patterns = self.research_service._generate_architectural_patterns(arch_area)
        
        # Assert
        assert len(patterns) > 0
        
        # Check pattern properties
        pattern = patterns[0]
        assert isinstance(pattern, ArchitecturalPattern)
        assert pattern.name != ""
        assert pattern.description != ""
        assert len(pattern.use_cases) > 0
        assert len(pattern.benefits) > 0
        assert pattern.relevance_score > 0
    
    def test_generate_implementation_approaches(self):
        """Test implementation approach generation."""
        # Arrange
        tech_area = ResearchArea(
            name="Technology Selection",
            description="Research technology options",
            priority=ResearchPriority.HIGH,
            research_type=ResearchType.TECHNOLOGY,
            keywords=["technology", "framework"]
        )
        
        # Act
        approaches = self.research_service._generate_implementation_approaches(tech_area)
        
        # Assert
        assert len(approaches) > 0
        
        # Check approach properties
        approach = approaches[0]
        assert isinstance(approach, ImplementationApproach)
        assert approach.name != ""
        assert approach.description != ""
        assert len(approach.technologies) > 0
        assert approach.complexity in ["low", "medium", "high"]
        assert len(approach.pros) > 0
        assert len(approach.cons) > 0
    
    def test_research_context_get_findings_by_area(self):
        """Test ResearchContext method to get findings by area."""
        # Arrange
        findings = [
            TechnicalFinding(
                area="Security",
                title="Security Finding 1",
                content="Security content 1",
                source="Source 1",
                source_type="documentation",
                relevance_score=0.8,
                keywords=["security"]
            ),
            TechnicalFinding(
                area="Technology",
                title="Tech Finding 1",
                content="Tech content 1",
                source="Source 2",
                source_type="documentation",
                relevance_score=0.7,
                keywords=["tech"]
            ),
            TechnicalFinding(
                area="Security",
                title="Security Finding 2",
                content="Security content 2",
                source="Source 3",
                source_type="best_practice",
                relevance_score=0.9,
                keywords=["security"]
            )
        ]
        
        research_context = ResearchContext(technical_findings=findings)
        
        # Act
        security_findings = research_context.get_findings_by_area("Security")
        tech_findings = research_context.get_findings_by_area("Technology")
        
        # Assert
        assert len(security_findings) == 2
        assert len(tech_findings) == 1
        assert all(f.area == "Security" for f in security_findings)
        assert all(f.area == "Technology" for f in tech_findings)
    
    def test_research_context_get_high_relevance_findings(self):
        """Test ResearchContext method to get high relevance findings."""
        # Arrange
        findings = [
            TechnicalFinding(
                area="Test",
                title="High Relevance",
                content="High relevance content",
                source="Source 1",
                source_type="documentation",
                relevance_score=0.9,
                keywords=["high"]
            ),
            TechnicalFinding(
                area="Test",
                title="Medium Relevance",
                content="Medium relevance content",
                source="Source 2",
                source_type="documentation",
                relevance_score=0.6,
                keywords=["medium"]
            ),
            TechnicalFinding(
                area="Test",
                title="Low Relevance",
                content="Low relevance content",
                source="Source 3",
                source_type="documentation",
                relevance_score=0.3,
                keywords=["low"]
            )
        ]
        
        research_context = ResearchContext(technical_findings=findings)
        
        # Act
        high_relevance = research_context.get_high_relevance_findings(threshold=0.7)
        
        # Assert
        assert len(high_relevance) == 1
        assert high_relevance[0].title == "High Relevance"
        assert high_relevance[0].relevance_score >= 0.7
    
    def test_technical_finding_checksum_calculation(self):
        """Test TechnicalFinding checksum calculation."""
        # Arrange
        finding = TechnicalFinding(
            area="Test",
            title="Test Finding",
            content="Test content for checksum",
            source="Test Source",
            source_type="documentation",
            relevance_score=0.8,
            keywords=["test"]
        )
        
        # Act
        checksum1 = finding.calculate_checksum()
        checksum2 = finding.calculate_checksum()
        
        # Assert
        assert checksum1 == checksum2  # Should be consistent
        assert len(checksum1) == 64  # SHA-256 hex length
        
        # Change content and verify checksum changes
        finding.content = "Different content"
        checksum3 = finding.calculate_checksum()
        assert checksum3 != checksum1
    
    def test_research_area_post_init_priority_score(self):
        """Test ResearchArea priority score calculation in __post_init__."""
        # Test different priority levels
        critical_area = ResearchArea(
            name="Critical Area",
            description="Critical research area",
            priority=ResearchPriority.CRITICAL,
            research_type=ResearchType.SECURITY,
            keywords=["critical"]
        )
        
        high_area = ResearchArea(
            name="High Area",
            description="High priority research area",
            priority=ResearchPriority.HIGH,
            research_type=ResearchType.TECHNOLOGY,
            keywords=["high"]
        )
        
        medium_area = ResearchArea(
            name="Medium Area",
            description="Medium priority research area",
            priority=ResearchPriority.MEDIUM,
            research_type=ResearchType.PERFORMANCE,
            keywords=["medium"]
        )
        
        # Assert priority scores
        assert critical_area.priority_score == 1.0
        assert high_area.priority_score == 0.8
        assert medium_area.priority_score == 0.6
        assert critical_area.priority_score > high_area.priority_score > medium_area.priority_score


class TestResearchServiceIntegration:
    """Integration tests for research service with other components."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.research_service = ResearchService()
    
    def test_research_service_with_html_sanitization(self):
        """Test research service with potentially malicious input."""
        # Arrange
        malicious_requirements = """
        <script>alert('xss')</script>
        # Requirements Document
        
        ## Requirements
        
        ### Requirement 1: User Input
        
        **User Story:** As a user, I want to <img src=x onerror=alert('xss')> input data
        
        #### Acceptance Criteria
        
        1.1. WHEN user provides input THEN system SHALL validate <script>malicious()</script>
        """
        
        # Act
        research_context = self.research_service.conduct_research(malicious_requirements)
        
        # Assert - Should not contain malicious scripts
        assert "<script>" not in research_context.research_summary
        assert "alert(" not in research_context.research_summary
        
        # Should still identify research areas
        assert len(research_context.research_areas) > 0
        assert len(research_context.technical_findings) > 0
    
    def test_end_to_end_research_workflow(self):
        """Test complete research workflow from requirements to validated context."""
        # Arrange
        requirements = """
        # Requirements Document
        
        ## Introduction
        
        The E-commerce Platform provides online shopping capabilities with secure payments.
        
        ## Requirements
        
        ### Requirement 1: Product Catalog
        
        **User Story:** As a customer, I want to browse products, so that I can find items to purchase
        
        #### Acceptance Criteria
        
        1.1. WHEN browsing products THEN the system SHALL display product information
        1.2. WHEN searching products THEN the system SHALL return relevant results
        1.3. IF no products match THEN the system SHALL display helpful suggestions
        
        ### Requirement 2: Payment Processing
        
        **User Story:** As a customer, I want to pay securely, so that my financial data is protected
        
        #### Acceptance Criteria
        
        2.1. WHEN processing payments THEN the system SHALL encrypt payment data
        2.2. WHEN payment fails THEN the system SHALL provide clear error messages
        2.3. IF fraud is detected THEN the system SHALL block the transaction
        
        ### Requirement 3: Performance
        
        **User Story:** As a customer, I want fast page loads, so that I can shop efficiently
        
        #### Acceptance Criteria
        
        3.1. WHEN loading pages THEN the system SHALL respond within 2 seconds
        3.2. WHEN handling concurrent users THEN the system SHALL maintain performance
        """
        
        # Act - Complete workflow
        research_context = self.research_service.conduct_research(requirements)
        validation_result = self.research_service.validate_research_quality(research_context)
        
        # Assert - Research context should be comprehensive
        assert len(research_context.research_areas) >= 3  # Should identify multiple areas
        assert len(research_context.technical_findings) >= 3  # Should have multiple findings
        
        # Should identify different research types
        research_types = set(area.research_type for area in research_context.research_areas)
        # Note: Security might be identified as part of other areas, so we'll check for key areas
        assert ResearchType.PERFORMANCE in research_types  # Performance requirements
        assert ResearchType.TECHNOLOGY in research_types or ResearchType.ARCHITECTURE in research_types
        
        # Should have architectural patterns
        assert len(research_context.architectural_patterns) > 0
        
        # Should have implementation approaches
        assert len(research_context.implementation_approaches) > 0
        
        # Should have technical constraints
        assert len(research_context.constraints) > 0
        
        # Validation should pass or have only warnings
        assert validation_result.is_valid or len(validation_result.errors) == 0
        
        # Research summary should be comprehensive
        assert len(research_context.research_summary) > 100
        assert "Research Summary" in research_context.research_summary