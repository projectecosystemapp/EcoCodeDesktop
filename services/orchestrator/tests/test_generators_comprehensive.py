"""
Comprehensive unit tests for document generators with various input scenarios.

This module provides extensive testing for requirements, design, and tasks generators
with diverse input scenarios, edge cases, and error conditions.

Requirements addressed:
- All requirements - validation through comprehensive testing
- Document generation with various input scenarios and edge cases
- EARS format validation, hierarchical numbering, and requirement traceability
"""

import pytest
import re
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock

from eco_api.specs.generators import (
    RequirementsGenerator, DesignGenerator, TasksGenerator, DocumentUpdateManager,
    UserStory, AcceptanceCriterion, Requirement, EARSFormat,
    ResearchArea, ResearchFinding, Task
)
from eco_api.specs.models import ValidationResult, ValidationError, ValidationWarning


class TestRequirementsGeneratorComprehensive:
    """Comprehensive tests for RequirementsGenerator with various input scenarios."""
    
    @pytest.fixture
    def generator(self):
        """Create RequirementsGenerator instance."""
        return RequirementsGenerator()
    
    @pytest.fixture
    def complex_feature_ideas(self):
        """Provide various complex feature ideas for testing."""
        return [
            "e-commerce platform with user authentication, product catalog, shopping cart, payment processing, order management, and admin dashboard",
            "real-time chat application with user presence, file sharing, message encryption, group chats, and mobile notifications",
            "project management tool with task tracking, team collaboration, time tracking, reporting, and integration with external services",
            "content management system with multi-user editing, version control, media management, SEO optimization, and plugin architecture",
            "financial dashboard with data visualization, portfolio tracking, risk analysis, automated alerts, and regulatory compliance"
        ]
    
    def test_generate_requirements_various_complexity_levels(self, generator, complex_feature_ideas):
        """Test requirements generation with various complexity levels."""
        for feature_idea in complex_feature_ideas:
            result = generator.generate_requirements_document(feature_idea)
            
            # Verify document structure
            assert "# Requirements Document" in result
            assert "## Introduction" in result
            assert "## Requirements" in result
            
            # Verify complexity is reflected in content length
            assert len(result) > 1000  # Complex features should generate substantial content
            
            # Verify multiple requirements are generated
            requirement_count = len(re.findall(r"### Requirement \d+:", result))
            assert requirement_count >= 3  # Complex features should have multiple requirements
            
            # Verify EARS format is used
            ears_patterns = ["WHEN", "THEN", "SHALL", "IF"]
            for pattern in ears_patterns:
                assert pattern in result
    
    def test_extract_key_concepts_comprehensive(self, generator):
        """Test comprehensive key concept extraction."""
        test_cases = [
            {
                "input": "admin dashboard for managing user accounts and permissions with role-based access control",
                "expected_actors": ["admin", "user"],
                "expected_actions": ["manage", "control", "access"],
                "expected_entities": ["dashboard", "accounts", "permissions", "roles"]
            },
            {
                "input": "mobile banking app with biometric authentication, transaction history, and bill payment",
                "expected_actors": ["user", "customer"],
                "expected_actions": ["authenticate", "pay", "view"],
                "expected_entities": ["app", "transactions", "bills", "biometric"]
            },
            {
                "input": "inventory management system for tracking products, suppliers, and warehouse operations",
                "expected_actors": ["manager", "operator", "supplier"],
                "expected_actions": ["track", "manage", "operate"],
                "expected_entities": ["inventory", "products", "warehouse"]
            }
        ]
        
        for test_case in test_cases:
            concepts = generator._extract_key_concepts(test_case["input"])
            
            # Verify actors are identified
            for expected_actor in test_case["expected_actors"]:
                assert any(expected_actor in actor.lower() for actor in concepts["actors"])
            
            # Verify actions are identified
            for expected_action in test_case["expected_actions"]:
                assert any(expected_action in action.lower() for action in concepts["actions"])
            
            # Verify entities are identified
            for expected_entity in test_case["expected_entities"]:
                assert any(expected_entity in entity.lower() for entity in concepts["entities"])
    
    def test_generate_introduction_various_domains(self, generator):
        """Test introduction generation for various domains."""
        domain_test_cases = [
            {
                "feature_idea": "healthcare patient management system",
                "concepts": {"actors": ["doctor", "patient", "nurse"], "actions": ["manage", "track", "schedule"]},
                "expected_keywords": ["healthcare", "patient", "medical", "clinical"]
            },
            {
                "feature_idea": "educational learning management system",
                "concepts": {"actors": ["teacher", "student", "admin"], "actions": ["learn", "teach", "assess"]},
                "expected_keywords": ["education", "learning", "course", "academic"]
            },
            {
                "feature_idea": "logistics fleet management platform",
                "concepts": {"actors": ["driver", "dispatcher", "manager"], "actions": ["track", "route", "deliver"]},
                "expected_keywords": ["logistics", "fleet", "delivery", "transportation"]
            }
        ]
        
        for test_case in domain_test_cases:
            intro = generator._generate_introduction(test_case["feature_idea"], test_case["concepts"])
            
            # Verify domain-specific keywords are present
            for keyword in test_case["expected_keywords"]:
                assert keyword.lower() in intro.lower()
            
            # Verify introduction is substantial and informative
            assert len(intro) > 200
            assert len(intro.split('.')) >= 3  # At least 3 sentences
    
    def test_create_requirements_various_types(self, generator):
        """Test creation of various requirement types."""
        feature_ideas_and_types = [
            ("user authentication system", ["functional", "security", "performance", "usability"]),
            ("data analytics dashboard", ["functional", "performance", "scalability", "integration"]),
            ("mobile payment app", ["functional", "security", "compliance", "usability", "performance"]),
            ("content delivery network", ["performance", "scalability", "reliability", "monitoring"])
        ]
        
        for feature_idea, expected_types in feature_ideas_and_types:
            concepts = generator._extract_key_concepts(feature_idea)
            requirements = generator._create_requirements_list(feature_idea, concepts)
            
            # Verify multiple requirement types are generated
            assert len(requirements) >= len(expected_types)
            
            # Verify each requirement has proper structure
            for requirement in requirements:
                assert requirement.id is not None
                assert requirement.title is not None
                assert requirement.user_story is not None
                assert len(requirement.acceptance_criteria) >= 2
                
                # Verify EARS format in acceptance criteria
                for criterion in requirement.acceptance_criteria:
                    assert criterion.format_type in [EARSFormat.WHEN_THEN, EARSFormat.IF_THEN, EARSFormat.GIVEN_WHEN_THEN]
    
    def test_ears_format_comprehensive(self, generator):
        """Test comprehensive EARS format generation."""
        test_scenarios = [
            {
                "condition": "user enters valid credentials",
                "action": "the system",
                "result": "authenticate the user successfully",
                "format": EARSFormat.WHEN_THEN,
                "expected": "WHEN user enters valid credentials THEN the system SHALL authenticate the user successfully"
            },
            {
                "condition": "the user is not authenticated",
                "action": "the system",
                "result": "redirect to login page",
                "format": EARSFormat.IF_THEN,
                "expected": "IF the user is not authenticated THEN the system SHALL redirect to login page"
            },
            {
                "condition": "user has admin privileges AND attempts to delete data",
                "action": "the system",
                "result": "prompt for confirmation before deletion",
                "format": EARSFormat.WHEN_THEN,
                "expected": "WHEN user has admin privileges AND attempts to delete data THEN the system SHALL prompt for confirmation before deletion"
            }
        ]
        
        for scenario in test_scenarios:
            criterion = AcceptanceCriterion(
                id="test",
                condition=scenario["condition"],
                action=scenario["action"],
                result=scenario["result"],
                format_type=scenario["format"]
            )
            
            markdown = criterion.to_markdown()
            assert scenario["expected"] in markdown
    
    def test_validate_requirements_format_edge_cases(self, generator):
        """Test requirements format validation with edge cases."""
        edge_cases = [
            {
                "name": "empty_document",
                "content": "",
                "should_be_valid": False,
                "expected_errors": ["missing", "empty"]
            },
            {
                "name": "only_title",
                "content": "# Requirements Document",
                "should_be_valid": False,
                "expected_errors": ["missing", "introduction"]
            },
            {
                "name": "malformed_user_stories",
                "content": """# Requirements Document

## Introduction

Test introduction.

## Requirements

### Requirement 1: Test

This is not a proper user story format.

#### Acceptance Criteria

1.1. WHEN something THEN system SHALL do something
""",
                "should_be_valid": False,
                "expected_errors": ["user story", "format"]
            },
            {
                "name": "missing_ears_format",
                "content": """# Requirements Document

## Introduction

Test introduction.

## Requirements

### Requirement 1: Test

**User Story:** As a user, I want something, so that I can achieve something

#### Acceptance Criteria

1.1. The system should do something
1.2. Users can perform actions
""",
                "should_be_valid": False,
                "expected_errors": ["EARS", "format", "SHALL"]
            }
        ]
        
        for case in edge_cases:
            result = generator.validate_requirements_format(case["content"])
            
            assert result.is_valid == case["should_be_valid"]
            
            if not case["should_be_valid"]:
                # Check that expected error keywords are present
                error_messages = " ".join([error.message.lower() for error in result.errors])
                for expected_error in case["expected_errors"]:
                    assert expected_error.lower() in error_messages
    
    def test_hierarchical_numbering_consistency(self, generator):
        """Test hierarchical numbering consistency across requirements."""
        feature_idea = "complex multi-module system with user management, content management, and reporting"
        
        result = generator.generate_requirements_document(feature_idea)
        
        # Extract all requirement numbers
        requirement_numbers = re.findall(r"### Requirement (\d+):", result)
        
        # Verify sequential numbering
        for i, num in enumerate(requirement_numbers, 1):
            assert int(num) == i
        
        # Extract all acceptance criteria numbers
        criteria_numbers = re.findall(r"(\d+\.\d+)\.", result)
        
        # Verify criteria numbering follows requirement numbering
        for criteria_num in criteria_numbers:
            req_num, criteria_seq = criteria_num.split('.')
            assert req_num in requirement_numbers
            assert int(criteria_seq) >= 1
    
    def test_requirement_traceability(self, generator):
        """Test requirement traceability and cross-references."""
        feature_idea = "integrated system with authentication, authorization, and audit logging"
        
        result = generator.generate_requirements_document(feature_idea)
        
        # Extract requirements and their IDs
        requirements = re.findall(r"### (Requirement \d+): (.+)", result)
        
        # Verify each requirement has unique ID
        requirement_ids = [req[0] for req in requirements]
        assert len(requirement_ids) == len(set(requirement_ids))
        
        # Verify acceptance criteria reference their parent requirement
        for req_id, req_title in requirements:
            req_num = req_id.split()[1]
            # Find acceptance criteria for this requirement
            criteria_pattern = rf"{req_num}\.(\d+)\."
            criteria_matches = re.findall(criteria_pattern, result)
            assert len(criteria_matches) >= 2  # Each requirement should have multiple criteria
    
    def test_error_handling_during_generation(self, generator):
        """Test error handling during requirements generation."""
        # Test with problematic inputs
        problematic_inputs = [
            None,
            "",
            "   ",
            "a" * 10000,  # Very long input
            "feature with special chars: !@#$%^&*(){}[]|\\:;\"'<>?,./",
            "feature\nwith\nmultiple\nlines\nand\ttabs"
        ]
        
        for problematic_input in problematic_inputs:
            try:
                result = generator.generate_requirements_document(problematic_input)
                # Should either succeed with sanitized input or handle gracefully
                assert isinstance(result, str)
            except Exception as e:
                # If exception is raised, it should be handled gracefully
                assert isinstance(e, (ValueError, TypeError))
    
    def test_performance_with_large_inputs(self, generator):
        """Test performance with large feature descriptions."""
        large_feature_idea = """
        Enterprise resource planning system with comprehensive modules including:
        - Human resources management with employee records, payroll, benefits, performance tracking
        - Financial management with accounting, budgeting, reporting, tax compliance
        - Supply chain management with procurement, inventory, vendor management
        - Customer relationship management with sales tracking, marketing automation
        - Project management with resource allocation, timeline tracking, collaboration tools
        - Business intelligence with data analytics, dashboards, predictive modeling
        - Document management with version control, workflow automation, compliance tracking
        - Integration capabilities with third-party systems, APIs, data synchronization
        - Security framework with role-based access, audit trails, data encryption
        - Mobile applications for field workers, managers, executives
        - Reporting engine with customizable reports, scheduled delivery, data export
        - Workflow automation with approval processes, notifications, escalations
        """ * 5  # Repeat to make it very large
        
        import time
        start_time = time.time()
        
        result = generator.generate_requirements_document(large_feature_idea)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert execution_time < 30  # 30 seconds max
        assert len(result) > 2000  # Should generate substantial content
        assert "# Requirements Document" in result


class TestDesignGeneratorComprehensive:
    """Comprehensive tests for DesignGenerator with various input scenarios."""
    
    @pytest.fixture
    def generator(self):
        """Create DesignGenerator instance."""
        return DesignGenerator()
    
    @pytest.fixture
    def sample_requirements_variations(self):
        """Provide various requirements documents for testing."""
        return [
            # Simple requirements
            """# Requirements Document

## Introduction

Simple user authentication system.

## Requirements

### Requirement 1: User Login

**User Story:** As a user, I want to log in, so that I can access the system

#### Acceptance Criteria

1.1. WHEN user enters valid credentials THEN system SHALL authenticate user
1.2. IF credentials are invalid THEN system SHALL display error message
""",
            # Complex requirements
            """# Requirements Document

## Introduction

Comprehensive e-commerce platform with multiple integrated modules.

## Requirements

### Requirement 1: User Management

**User Story:** As a customer, I want to manage my account, so that I can control my profile and preferences

#### Acceptance Criteria

1.1. WHEN user registers THEN system SHALL create account with email verification
1.2. WHEN user updates profile THEN system SHALL validate and save changes
1.3. IF user forgets password THEN system SHALL provide secure reset mechanism

### Requirement 2: Product Catalog

**User Story:** As a customer, I want to browse products, so that I can find items to purchase

#### Acceptance Criteria

2.1. WHEN user searches products THEN system SHALL return relevant results with filtering
2.2. WHEN user views product THEN system SHALL display detailed information and reviews
2.3. IF product is out of stock THEN system SHALL show availability status

### Requirement 3: Shopping Cart

**User Story:** As a customer, I want to manage my cart, so that I can prepare for checkout

#### Acceptance Criteria

3.1. WHEN user adds item THEN system SHALL update cart with quantity and pricing
3.2. WHEN user modifies cart THEN system SHALL recalculate totals immediately
3.3. IF cart is abandoned THEN system SHALL save cart state for later retrieval
""",
            # Security-focused requirements
            """# Requirements Document

## Introduction

High-security financial application with strict compliance requirements.

## Requirements

### Requirement 1: Authentication Security

**User Story:** As a user, I want secure authentication, so that my financial data is protected

#### Acceptance Criteria

1.1. WHEN user logs in THEN system SHALL require multi-factor authentication
1.2. WHEN suspicious activity detected THEN system SHALL lock account and notify user
1.3. IF authentication fails multiple times THEN system SHALL implement progressive delays

### Requirement 2: Data Encryption

**User Story:** As a user, I want my data encrypted, so that it remains confidential

#### Acceptance Criteria

2.1. WHEN data is stored THEN system SHALL encrypt using AES-256 encryption
2.2. WHEN data is transmitted THEN system SHALL use TLS 1.3 or higher
2.3. IF encryption keys expire THEN system SHALL rotate keys automatically
"""
        ]
    
    def test_generate_design_various_complexity_levels(self, generator, sample_requirements_variations):
        """Test design generation with various complexity levels."""
        for i, requirements in enumerate(sample_requirements_variations):
            result = generator.generate_design_document(requirements)
            
            # Verify all required sections are present
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
                assert section in result, f"Missing section {section} in complexity level {i}"
            
            # Verify content scales with complexity
            if i == 0:  # Simple requirements
                assert 1500 <= len(result) <= 4000
            elif i == 1:  # Complex requirements
                assert len(result) >= 3000
            elif i == 2:  # Security-focused requirements
                assert "security" in result.lower()
                assert "encryption" in result.lower()
    
    def test_parse_requirements_comprehensive(self, generator, sample_requirements_variations):
        """Test comprehensive requirements parsing."""
        for requirements in sample_requirements_variations:
            info = generator._parse_requirements(requirements)
            
            # Verify basic structure
            assert "feature_name" in info
            assert "user_stories" in info
            assert "acceptance_criteria" in info
            assert "actors" in info
            assert "actions" in info
            
            # Verify content extraction
            assert len(info["user_stories"]) > 0
            assert len(info["acceptance_criteria"]) > 0
            assert len(info["actors"]) > 0
            
            # Verify actors are properly identified
            common_actors = ["user", "customer", "admin", "system"]
            identified_actors = [actor.lower() for actor in info["actors"]]
            assert any(actor in identified_actors for actor in common_actors)
    
    def test_identify_research_areas_domain_specific(self, generator):
        """Test research area identification for different domains."""
        domain_test_cases = [
            {
                "requirements_info": {
                    "actions": {"authenticate", "encrypt", "authorize", "audit"},
                    "data_entities": {"user", "credentials", "tokens", "logs"},
                    "feature_name": "Security System"
                },
                "expected_areas": ["authentication", "encryption", "security", "compliance"]
            },
            {
                "requirements_info": {
                    "actions": {"process", "analyze", "visualize", "report"},
                    "data_entities": {"data", "metrics", "charts", "dashboards"},
                    "feature_name": "Analytics Platform"
                },
                "expected_areas": ["data processing", "visualization", "analytics", "performance"]
            },
            {
                "requirements_info": {
                    "actions": {"stream", "encode", "deliver", "cache"},
                    "data_entities": {"video", "audio", "content", "bandwidth"},
                    "feature_name": "Media Streaming"
                },
                "expected_areas": ["streaming", "encoding", "cdn", "performance"]
            }
        ]
        
        for test_case in domain_test_cases:
            research_context = generator._identify_research_areas(test_case["requirements_info"])
            
            # Verify research areas are identified
            assert "areas" in research_context
            assert len(research_context["areas"]) > 0
            
            # Verify domain-specific areas are included
            research_areas_text = " ".join(research_context["areas"]).lower()
            for expected_area in test_case["expected_areas"]:
                assert expected_area.lower() in research_areas_text
    
    def test_generate_architecture_various_patterns(self, generator):
        """Test architecture generation with various architectural patterns."""
        architecture_test_cases = [
            {
                "requirements_info": {"feature_name": "Microservices E-commerce"},
                "research_context": {
                    "technology_recommendations": {
                        "architecture": "microservices",
                        "backend": "FastAPI with Docker",
                        "frontend": "React with TypeScript",
                        "database": "PostgreSQL with Redis cache"
                    },
                    "architectural_patterns": [
                        "Microservices Architecture: Service decomposition",
                        "API Gateway Pattern: Centralized routing",
                        "Event Sourcing: Audit trail and state reconstruction"
                    ]
                },
                "expected_keywords": ["microservices", "api gateway", "event sourcing", "docker"]
            },
            {
                "requirements_info": {"feature_name": "Monolithic CMS"},
                "research_context": {
                    "technology_recommendations": {
                        "architecture": "monolithic",
                        "backend": "Django with PostgreSQL",
                        "frontend": "Server-side rendering"
                    },
                    "architectural_patterns": [
                        "Layered Architecture: Clear separation of concerns",
                        "MVC Pattern: Model-View-Controller structure"
                    ]
                },
                "expected_keywords": ["layered", "mvc", "monolithic", "django"]
            }
        ]
        
        for test_case in architecture_test_cases:
            architecture = generator._generate_architecture(
                test_case["requirements_info"], 
                test_case["research_context"]
            )
            
            # Verify architecture content includes expected patterns
            architecture_lower = architecture.lower()
            for keyword in test_case["expected_keywords"]:
                assert keyword.lower() in architecture_lower
            
            # Verify standard architecture sections
            assert "System Boundaries" in architecture
            assert "Technology Stack" in architecture
    
    def test_generate_components_and_interfaces(self, generator):
        """Test component and interface generation."""
        requirements_info = {
            "feature_name": "User Management System",
            "actors": ["user", "admin"],
            "actions": ["authenticate", "manage", "validate"],
            "data_entities": ["user", "profile", "permissions"]
        }
        
        research_context = {
            "technology_recommendations": {
                "backend": "FastAPI",
                "frontend": "React",
                "database": "PostgreSQL"
            }
        }
        
        components = generator._generate_components_and_interfaces(requirements_info, research_context)
        
        # Verify component structure
        assert "#### 1." in components  # Numbered components
        assert "interface" in components.lower() or "api" in components.lower()
        
        # Verify domain-specific components are mentioned
        assert "user" in components.lower()
        assert "authentication" in components.lower() or "auth" in components.lower()
    
    def test_generate_data_models_comprehensive(self, generator):
        """Test comprehensive data model generation."""
        requirements_info = {
            "data_entities": ["user", "product", "order", "payment", "review"],
            "actions": {"create", "read", "update", "delete", "validate"},
            "relationships": ["user-order", "product-review", "order-payment"]
        }
        
        research_context = {
            "technology_recommendations": {
                "database": "PostgreSQL with SQLAlchemy ORM"
            }
        }
        
        data_models = generator._generate_data_models(requirements_info, research_context)
        
        # Verify data model content
        assert "User" in data_models or "user" in data_models.lower()
        assert "Product" in data_models or "product" in data_models.lower()
        
        # Verify relationships are mentioned
        assert "relationship" in data_models.lower() or "foreign key" in data_models.lower()
        
        # Verify validation is mentioned
        assert "validation" in data_models.lower()
    
    def test_validate_design_format_comprehensive(self, generator):
        """Test comprehensive design format validation."""
        validation_test_cases = [
            {
                "name": "complete_valid_design",
                "content": """# Design Document

## Overview

Comprehensive overview of the system architecture and design decisions.

## Architecture

### System Boundaries

Clear definition of system boundaries and external interfaces.

### Technology Stack

- Backend: FastAPI with Python
- Frontend: React with TypeScript
- Database: PostgreSQL

## Components and Interfaces

### Core Components

#### 1. Authentication Service
Handles user authentication and authorization.

#### 2. Data Access Layer
Manages database interactions and data persistence.

## Data Models

### User Model
- id: Primary key
- email: Unique identifier
- password_hash: Encrypted password

### Relationships
- User has many Orders
- Order belongs to User

## Error Handling

### Error Categories
1. Validation Errors
2. Authentication Errors
3. System Errors

### Error Response Format
All errors follow consistent JSON structure.

## Testing Strategy

### Unit Testing
- Component isolation testing
- Mock external dependencies

### Integration Testing
- API endpoint testing
- Database integration testing

### End-to-End Testing
- User workflow testing
- Performance testing
""",
                "should_be_valid": True,
                "expected_warnings": []
            },
            {
                "name": "missing_required_sections",
                "content": """# Design Document

## Overview

Basic overview only.

## Architecture

Some architecture content.
""",
                "should_be_valid": False,
                "expected_errors": ["Components and Interfaces", "Data Models", "Error Handling", "Testing Strategy"]
            },
            {
                "name": "empty_sections",
                "content": """# Design Document

## Overview

## Architecture

## Components and Interfaces

## Data Models

## Error Handling

## Testing Strategy
""",
                "should_be_valid": False,
                "expected_errors": ["empty", "content"]
            }
        ]
        
        for test_case in validation_test_cases:
            result = generator.validate_design_format(test_case["content"])
            
            assert result.is_valid == test_case["should_be_valid"]
            
            if not test_case["should_be_valid"]:
                error_messages = " ".join([error.message for error in result.errors])
                for expected_error in test_case["expected_errors"]:
                    assert expected_error in error_messages
    
    def test_research_integration_comprehensive(self, generator):
        """Test comprehensive research integration into design."""
        requirements_with_research_needs = """# Requirements Document

## Introduction

Advanced AI-powered recommendation system with real-time processing.

## Requirements

### Requirement 1: Machine Learning Integration

**User Story:** As a user, I want personalized recommendations, so that I can discover relevant content

#### Acceptance Criteria

1.1. WHEN user interacts with content THEN system SHALL update recommendation model
1.2. WHEN generating recommendations THEN system SHALL use collaborative filtering
1.3. IF user preferences change THEN system SHALL adapt recommendations accordingly

### Requirement 2: Real-time Processing

**User Story:** As a user, I want instant recommendations, so that I can get immediate value

#### Acceptance Criteria

2.1. WHEN user requests recommendations THEN system SHALL respond within 100ms
2.2. WHEN processing user data THEN system SHALL handle concurrent requests
2.3. IF system load is high THEN system SHALL maintain response time SLA
"""
        
        result = generator.generate_design_document(requirements_with_research_needs)
        
        # Verify research-informed content
        result_lower = result.lower()
        
        # Should include ML/AI related architecture decisions
        ml_keywords = ["machine learning", "recommendation", "algorithm", "model", "training"]
        assert any(keyword in result_lower for keyword in ml_keywords)
        
        # Should include performance considerations
        performance_keywords = ["performance", "latency", "scalability", "caching", "optimization"]
        assert any(keyword in result_lower for keyword in performance_keywords)
        
        # Should include real-time processing architecture
        realtime_keywords = ["real-time", "streaming", "concurrent", "async", "queue"]
        assert any(keyword in result_lower for keyword in realtime_keywords)


class TestTasksGeneratorComprehensive:
    """Comprehensive tests for TasksGenerator with various input scenarios."""
    
    @pytest.fixture
    def generator(self):
        """Create TasksGenerator instance."""
        return TasksGenerator()
    
    @pytest.fixture
    def requirements_design_pairs(self):
        """Provide various requirements-design pairs for testing."""
        return [
            {
                "requirements": """# Requirements Document

## Introduction

Simple web application with user authentication.

## Requirements

### Requirement 1: User Authentication

**User Story:** As a user, I want to log in securely, so that I can access my account

#### Acceptance Criteria

1.1. WHEN user enters credentials THEN system SHALL validate against database
1.2. IF credentials are valid THEN system SHALL create session token
1.3. IF credentials are invalid THEN system SHALL display error message
""",
                "design": """# Design Document

## Overview

Simple web application using React frontend and FastAPI backend.

## Architecture

### Technology Stack
- Frontend: React with TypeScript
- Backend: FastAPI with Python
- Database: PostgreSQL
- Authentication: JWT tokens

## Components and Interfaces

#### 1. Authentication Service
Handles user login and token management.

#### 2. User Interface Components
React components for login forms and user dashboard.

## Data Models

### User Model
- id: Primary key
- email: Unique identifier
- password_hash: Encrypted password

## Error Handling

Standard HTTP error responses with JSON format.

## Testing Strategy

Unit tests for components, integration tests for API endpoints.
""",
                "expected_task_count": 8,
                "expected_keywords": ["react", "fastapi", "authentication", "jwt", "postgresql"]
            },
            {
                "requirements": """# Requirements Document

## Introduction

Complex e-commerce platform with multiple integrated modules.

## Requirements

### Requirement 1: Product Management

**User Story:** As an admin, I want to manage products, so that I can maintain the catalog

#### Acceptance Criteria

1.1. WHEN admin adds product THEN system SHALL validate and store product data
1.2. WHEN admin updates product THEN system SHALL maintain version history
1.3. IF product has variants THEN system SHALL manage variant relationships

### Requirement 2: Order Processing

**User Story:** As a customer, I want to place orders, so that I can purchase products

#### Acceptance Criteria

2.1. WHEN customer places order THEN system SHALL validate inventory availability
2.2. WHEN order is confirmed THEN system SHALL initiate payment processing
2.3. IF payment fails THEN system SHALL handle order cancellation gracefully

### Requirement 3: Inventory Management

**User Story:** As a manager, I want to track inventory, so that I can maintain stock levels

#### Acceptance Criteria

3.1. WHEN product is sold THEN system SHALL update inventory counts
3.2. WHEN inventory is low THEN system SHALL trigger reorder notifications
3.3. IF product is out of stock THEN system SHALL update product availability
""",
                "design": """# Design Document

## Overview

Microservices-based e-commerce platform with event-driven architecture.

## Architecture

### Technology Stack
- Frontend: React with Next.js
- Backend: Multiple FastAPI microservices
- Database: PostgreSQL with Redis cache
- Message Queue: RabbitMQ
- Search: Elasticsearch

### Microservices
1. Product Service
2. Order Service
3. Inventory Service
4. Payment Service
5. User Service

## Components and Interfaces

#### 1. Product Management Service
Handles product CRUD operations and catalog management.

#### 2. Order Processing Service
Manages order lifecycle and state transitions.

#### 3. Inventory Service
Tracks stock levels and availability.

#### 4. API Gateway
Routes requests to appropriate microservices.

## Data Models

### Product Model
- Complex product hierarchy with variants
- Category relationships
- Pricing and inventory links

### Order Model
- Order items and quantities
- Payment and shipping information
- Status tracking

## Error Handling

Distributed error handling with circuit breakers and retry mechanisms.

## Testing Strategy

Comprehensive testing including unit, integration, contract, and end-to-end tests.
""",
                "expected_task_count": 15,
                "expected_keywords": ["microservices", "rabbitmq", "elasticsearch", "redis", "next.js"]
            }
        ]
    
    def test_generate_tasks_various_complexity_levels(self, generator, requirements_design_pairs):
        """Test task generation with various complexity levels."""
        for i, pair in enumerate(requirements_design_pairs):
            result = generator.generate_tasks_document(pair["requirements"], pair["design"])
            
            # Verify document structure
            assert "# Implementation Plan" in result
            
            # Verify task count scales with complexity
            checkbox_pattern = r"- \[ \] \d+(\.\d+)?\. .+"
            checkboxes = re.findall(checkbox_pattern, result)
            assert len(checkboxes) >= pair["expected_task_count"]
            
            # Verify technology-specific tasks are included
            result_lower = result.lower()
            for keyword in pair["expected_keywords"]:
                assert keyword.lower() in result_lower
            
            # Verify requirement references
            assert "_Requirements:" in result
            
            # Verify proper task hierarchy
            main_tasks = re.findall(r"- \[ \] (\d+)\. ", result)
            subtasks = re.findall(r"- \[ \] (\d+\.\d+) ", result)
            
            assert len(main_tasks) >= 3  # Should have multiple main tasks
            assert len(subtasks) >= len(main_tasks)  # Should have subtasks
    
    def test_parse_requirements_for_tasks_comprehensive(self, generator, requirements_design_pairs):
        """Test comprehensive requirements parsing for task generation."""
        for pair in requirements_design_pairs:
            info = generator._parse_requirements_for_tasks(pair["requirements"])
            
            # Verify structure
            assert "requirements" in info
            assert "functional_areas" in info
            assert "complexity_indicators" in info
            
            # Verify requirements extraction
            assert len(info["requirements"]) > 0
            
            for requirement in info["requirements"]:
                assert "id" in requirement
                assert "title" in requirement
                assert "criteria" in requirement
                assert len(requirement["criteria"]) > 0
            
            # Verify functional areas identification
            assert len(info["functional_areas"]) > 0
    
    def test_parse_design_for_tasks_comprehensive(self, generator, requirements_design_pairs):
        """Test comprehensive design parsing for task generation."""
        for pair in requirements_design_pairs:
            info = generator._parse_design_for_tasks(pair["design"])
            
            # Verify structure
            assert "components" in info
            assert "technology_stack" in info
            assert "architectural_patterns" in info
            
            # Verify technology stack extraction
            assert len(info["technology_stack"]) > 0
            
            # Verify components extraction
            assert len(info["components"]) > 0
            
            # Verify architectural patterns
            if "microservices" in pair["design"].lower():
                assert any("microservice" in pattern.lower() for pattern in info["architectural_patterns"])
    
    def test_generate_task_hierarchy_comprehensive(self, generator):
        """Test comprehensive task hierarchy generation."""
        requirements_info = {
            "functional_areas": {"authentication", "product_management", "order_processing", "inventory_management"},
            "requirements": [
                {"id": "Requirement 1", "title": "Authentication", "criteria": ["1.1", "1.2", "1.3"]},
                {"id": "Requirement 2", "title": "Product Management", "criteria": ["2.1", "2.2"]},
                {"id": "Requirement 3", "title": "Order Processing", "criteria": ["3.1", "3.2", "3.3", "3.4"]}
            ],
            "complexity_indicators": {"high_complexity": True, "multiple_services": True}
        }
        
        design_info = {
            "technology_stack": {
                "frontend": "React with TypeScript",
                "backend": "FastAPI microservices",
                "database": "PostgreSQL with Redis",
                "message_queue": "RabbitMQ"
            },
            "components": [
                {"name": "Authentication Service", "type": "microservice"},
                {"name": "Product Service", "type": "microservice"},
                {"name": "Order Service", "type": "microservice"},
                {"name": "API Gateway", "type": "infrastructure"}
            ],
            "architectural_patterns": ["Microservices", "Event-driven", "CQRS"]
        }
        
        tasks = generator._generate_task_hierarchy(requirements_info, design_info)
        
        # Verify task structure
        assert len(tasks) >= 5  # Should have multiple main tasks
        
        # Verify task categories are covered
        task_descriptions = " ".join([task.description for task in tasks]).lower()
        expected_categories = ["infrastructure", "authentication", "product", "order", "testing"]
        
        for category in expected_categories:
            assert category in task_descriptions
        
        # Verify subtask structure
        subtask_count = sum(len(task.subtasks) for task in tasks)
        assert subtask_count >= len(tasks) * 2  # Each main task should have multiple subtasks
        
        # Verify requirement traceability
        all_requirements = []
        for task in tasks:
            all_requirements.extend(task.requirements)
            for subtask in task.subtasks:
                all_requirements.extend(subtask.requirements)
        
        assert len(all_requirements) > 0
        assert any(req.startswith("1.") for req in all_requirements)  # References to requirement 1
    
    def test_validate_tasks_format_comprehensive(self, generator):
        """Test comprehensive task format validation."""
        validation_test_cases = [
            {
                "name": "valid_tasks_with_hierarchy",
                "content": """# Implementation Plan

- [ ] 1. Set up project infrastructure
  - Create project structure with proper directory organization
  - Configure build tools and development environment
  - Set up version control and CI/CD pipeline
  - _Requirements: 1.1, 1.2_

- [ ] 1.1 Configure development environment
  - Install and configure Node.js and Python environments
  - Set up database connections and migrations
  - Configure environment variables and secrets management
  - _Requirements: 1.1_

- [ ] 1.2 Implement core authentication system
  - Create user model and database schema
  - Implement JWT token generation and validation
  - Add password hashing and security measures
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 2. Build user interface components
  - Create React components for authentication forms
  - Implement responsive design and accessibility features
  - Add form validation and error handling
  - _Requirements: 2.1, 2.2_
""",
                "should_be_valid": True,
                "expected_warnings": []
            },
            {
                "name": "tasks_with_non_coding_activities",
                "content": """# Implementation Plan

- [ ] 1. Conduct user research and interviews
  - Interview potential users about requirements
  - Analyze market competition and trends
  - _Requirements: 1.1_

- [ ] 2. Deploy application to production
  - Set up production servers and infrastructure
  - Configure monitoring and alerting systems
  - _Requirements: 2.1_

- [ ] 3. Gather performance metrics from users
  - Monitor user behavior and system usage
  - Collect feedback through surveys
  - _Requirements: 3.1_
""",
                "should_be_valid": False,
                "expected_errors": ["non-coding activity", "user research", "deployment", "metrics gathering"]
            },
            {
                "name": "missing_requirement_references",
                "content": """# Implementation Plan

- [ ] 1. Set up project structure
  - Create directories and files
  - Configure build tools

- [ ] 2. Implement authentication
  - Create login functionality
  - Add security measures
""",
                "should_be_valid": False,
                "expected_errors": ["missing requirement references", "_Requirements:"]
            },
            {
                "name": "invalid_task_numbering",
                "content": """# Implementation Plan

- [ ] 1. First task
  - Task details
  - _Requirements: 1.1_

- [ ] 3. Third task (skipped 2)
  - Task details
  - _Requirements: 1.2_

- [ ] 1.5 Invalid subtask numbering
  - Task details
  - _Requirements: 1.1_
""",
                "should_be_valid": False,
                "expected_errors": ["numbering", "sequence"]
            }
        ]
        
        for test_case in validation_test_cases:
            result = generator.validate_tasks_format(test_case["content"])
            
            assert result.is_valid == test_case["should_be_valid"]
            
            if not test_case["should_be_valid"]:
                error_messages = " ".join([error.message.lower() for error in result.errors])
                for expected_error in test_case["expected_errors"]:
                    assert expected_error.lower() in error_messages
    
    def test_task_sequencing_and_dependencies(self, generator):
        """Test task sequencing and dependency management."""
        requirements_info = {
            "functional_areas": {"infrastructure", "backend", "frontend", "testing"},
            "requirements": [
                {"id": "Requirement 1", "title": "Infrastructure", "criteria": ["1.1", "1.2"]},
                {"id": "Requirement 2", "title": "Backend API", "criteria": ["2.1", "2.2", "2.3"]},
                {"id": "Requirement 3", "title": "Frontend UI", "criteria": ["3.1", "3.2"]},
                {"id": "Requirement 4", "title": "Testing", "criteria": ["4.1", "4.2"]}
            ]
        }
        
        design_info = {
            "technology_stack": {"frontend": "React", "backend": "FastAPI", "database": "PostgreSQL"},
            "components": [
                {"name": "Database Layer", "dependencies": []},
                {"name": "API Layer", "dependencies": ["Database Layer"]},
                {"name": "Frontend Layer", "dependencies": ["API Layer"]}
            ]
        }
        
        tasks = generator._generate_task_hierarchy(requirements_info, design_info)
        
        # Verify logical sequencing
        task_descriptions = [task.description.lower() for task in tasks]
        
        # Infrastructure should come first
        infrastructure_index = next(i for i, desc in enumerate(task_descriptions) if "infrastructure" in desc or "setup" in desc)
        
        # Backend should come before frontend
        backend_indices = [i for i, desc in enumerate(task_descriptions) if "api" in desc or "backend" in desc or "service" in desc]
        frontend_indices = [i for i, desc in enumerate(task_descriptions) if "frontend" in desc or "ui" in desc or "react" in desc]
        
        if backend_indices and frontend_indices:
            assert min(backend_indices) < min(frontend_indices)
        
        # Testing should come after implementation
        testing_indices = [i for i, desc in enumerate(task_descriptions) if "test" in desc]
        implementation_indices = [i for i, desc in enumerate(task_descriptions) if "implement" in desc or "create" in desc]
        
        if testing_indices and implementation_indices:
            # At least some testing should come after implementation
            assert max(implementation_indices) < max(testing_indices)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])