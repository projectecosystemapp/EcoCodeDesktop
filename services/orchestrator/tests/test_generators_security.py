"""
Tests for security aspects of document generators.

This module tests that the document generators properly sanitize user input
to prevent XSS attacks and other security vulnerabilities.
"""

import pytest
from eco_api.specs.generators import (
    RequirementsGenerator, 
    DesignGenerator, 
    TasksGenerator,
    UserStory,
    AcceptanceCriterion,
    EARSFormat,
    Requirement
)


class TestRequirementsGeneratorSecurity:
    """Test security aspects of RequirementsGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = RequirementsGenerator()
    
    def test_sanitizes_malicious_feature_idea(self):
        """Test that malicious feature ideas are sanitized."""
        malicious_idea = "<script>alert('xss')</script>User management system"
        
        result = self.generator.generate_requirements_document(malicious_idea)
        
        # Should not contain executable script
        assert "<script>" not in result
        assert "alert('xss')" not in result
        assert "[SCRIPT_REMOVED]" in result or "&lt;script&gt;" in result
    
    def test_sanitizes_feature_idea_with_html_injection(self):
        """Test that HTML injection attempts are sanitized."""
        malicious_idea = "User system <img src=x onerror=alert('xss')>"
        
        result = self.generator.generate_requirements_document(malicious_idea)
        
        # Should not contain executable content
        assert "onerror=" not in result
        assert "[SCRIPT_REMOVED]" in result or "&lt;img" in result
    
    def test_sanitizes_javascript_protocol(self):
        """Test that javascript: protocol is sanitized."""
        malicious_idea = "System with javascript:alert('xss') functionality"
        
        result = self.generator.generate_requirements_document(malicious_idea)
        
        # Should not contain javascript protocol
        assert "javascript:alert" not in result
        assert "[SCRIPT_REMOVED]" in result
    
    def test_preserves_safe_content(self):
        """Test that safe content is preserved."""
        safe_idea = "User management system with authentication"
        
        result = self.generator.generate_requirements_document(safe_idea)
        
        # Should contain the safe content
        assert "User management system" in result
        assert "authentication" in result
        assert "[SCRIPT_REMOVED]" not in result


class TestDesignGeneratorSecurity:
    """Test security aspects of DesignGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = DesignGenerator()
    
    def test_sanitizes_malicious_requirements_content(self):
        """Test that malicious requirements content is sanitized."""
        malicious_requirements = """
        # Requirements Document
        
        ## Introduction
        
        <script>alert('xss')</script>This is a test feature.
        
        ## Requirements
        
        ### Requirement 1: User Management
        
        **User Story:** As a user, I want <iframe src=javascript:alert('xss')></iframe> functionality.
        """
        
        result = self.generator.generate_design_document(malicious_requirements)
        
        # Should not contain executable content
        assert "<script>" not in result
        assert "<iframe" not in result
        # The malicious content should be sanitized - either removed or escaped
        # Since the design generator processes sanitized input, it may not show markers
        # but it should not contain the original malicious patterns
        assert "alert('xss')" not in result
    
    def test_sanitizes_malicious_research_context(self):
        """Test that malicious research context is sanitized."""
        safe_requirements = """
        # Requirements Document
        
        ## Introduction
        
        This is a safe feature.
        """
        
        malicious_research = {
            "findings": "<script>alert('research xss')</script>Important research",
            "sources": ["javascript:alert('source xss')"]
        }
        
        result = self.generator.generate_design_document(safe_requirements, malicious_research)
        
        # Should not contain executable content
        assert "<script>" not in result
        assert "alert('research xss')" not in result
        assert "javascript:alert('source xss')" not in result


class TestTasksGeneratorSecurity:
    """Test security aspects of TasksGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TasksGenerator()
    
    def test_sanitizes_malicious_requirements_and_design(self):
        """Test that malicious requirements and design content is sanitized."""
        malicious_requirements = """
        # Requirements Document
        
        <script>alert('req xss')</script>
        
        ### Requirement 1: Test
        """
        
        malicious_design = """
        # Design Document
        
        <iframe src=javascript:alert('design xss')></iframe>
        
        ## Overview
        """
        
        result = self.generator.generate_tasks_document(malicious_requirements, malicious_design)
        
        # Should not contain executable content
        assert "<script>" not in result
        assert "<iframe" not in result
        assert "alert('req xss')" not in result
        assert "alert('design xss')" not in result


class TestDataClassesSecurity:
    """Test security aspects of data classes."""
    
    def test_user_story_sanitizes_content(self):
        """Test that UserStory sanitizes content in to_markdown."""
        malicious_story = UserStory(
            role="<script>alert('role')</script>user",
            feature="<img src=x onerror=alert('feature')>manage data",
            benefit="<iframe src=javascript:alert('benefit')></iframe>"
        )
        
        result = malicious_story.to_markdown()
        
        # Should not contain executable content
        assert "<script>" not in result
        assert "onerror=" not in result
        assert "<iframe" not in result
        # Should contain escaped content
        assert "&lt;script&gt;" in result or "&lt;img" in result or "&lt;iframe" in result
    
    def test_acceptance_criterion_sanitizes_content(self):
        """Test that AcceptanceCriterion sanitizes content in to_markdown."""
        malicious_criterion = AcceptanceCriterion(
            id="<script>alert('id')</script>1.1",
            condition="<iframe src=javascript:alert('condition')>user clicks",
            action="system<img src=x onerror=alert('action')>",
            result="<object data=javascript:alert('result')>",
            format_type=EARSFormat.WHEN_THEN
        )
        
        result = malicious_criterion.to_markdown()
        
        # Should not contain executable content
        assert "<script>" not in result
        assert "<iframe" not in result
        assert "onerror=" not in result
        assert "<object" not in result
        # Should contain escaped content
        assert "&lt;" in result
    
    def test_requirement_sanitizes_title(self):
        """Test that Requirement sanitizes title in to_markdown."""
        safe_story = UserStory(
            role="user",
            feature="manage data",
            benefit="efficiency"
        )
        
        safe_criterion = AcceptanceCriterion(
            id="1.1",
            condition="user clicks button",
            action="system",
            result="respond",
            format_type=EARSFormat.WHEN_THEN
        )
        
        malicious_requirement = Requirement(
            id="req1",
            title="<script>alert('title')</script>User Management",
            user_story=safe_story,
            acceptance_criteria=[safe_criterion]
        )
        
        result = malicious_requirement.to_markdown()
        
        # Should not contain executable content in title
        assert "<script>" not in result
        assert "&lt;script&gt;" in result


class TestSecurityIntegration:
    """Test end-to-end security integration."""
    
    def test_full_workflow_security(self):
        """Test security through the full document generation workflow."""
        # Malicious input that tries multiple attack vectors
        malicious_input = """
        <script>alert('xss1')</script>
        User management system with 
        <img src=x onerror=alert('xss2')>
        javascript:alert('xss3')
        <iframe src=javascript:alert('xss4')></iframe>
        {{constructor.constructor('alert(5)')()}}
        """
        
        # Generate requirements
        req_gen = RequirementsGenerator()
        requirements = req_gen.generate_requirements_document(malicious_input)
        
        # Generate design
        design_gen = DesignGenerator()
        design = design_gen.generate_design_document(requirements)
        
        # Generate tasks
        tasks_gen = TasksGenerator()
        tasks = tasks_gen.generate_tasks_document(requirements, design)
        
        # Verify all outputs are safe
        for document in [requirements, design, tasks]:
            assert "<script>" not in document
            assert "onerror=" not in document
            assert "<iframe" not in document
            # Should not contain the specific malicious alert calls in executable form
            assert "alert('xss1')" not in document
            assert "alert('xss2')" not in document
            assert "alert('xss3')" not in document
            assert "alert('xss4')" not in document
            # Check that constructor injection is neutralized
            assert "constructor.constructor('alert(5)')" not in document
    
    def test_nested_attack_prevention(self):
        """Test prevention of nested and sophisticated attacks."""
        sophisticated_attack = """
        Feature: <scr<script>ipt>alert('nested')</script>
        With: <<SCRIPT>alert('double');//<</SCRIPT>
        And: %3Cscript%3Ealert('encoded')%3C/script%3E
        Plus: &#60;script&#62;alert('entity')&#60;/script&#62;
        """
        
        req_gen = RequirementsGenerator()
        result = req_gen.generate_requirements_document(sophisticated_attack)
        
        # Should neutralize all attack vectors
        assert "alert('nested')" not in result
        assert "alert('double')" not in result
        assert "alert('encoded')" not in result
        assert "alert('entity')" not in result
        assert "[SCRIPT_REMOVED]" in result or "&lt;" in result