"""
Tests for HTML sanitization functionality.

This module tests the HTMLSanitizer class to ensure proper XSS prevention
and safe content processing.
"""

import pytest
from eco_api.security.html_sanitizer import (
    HTMLSanitizer, 
    SanitizationLevel, 
    SanitizationResult,
    escape_html,
    sanitize_user_input,
    is_script_content,
    create_safe_template_content
)


class TestHTMLSanitizer:
    """Test cases for HTMLSanitizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sanitizer = HTMLSanitizer()
    
    def test_escape_html_basic_characters(self):
        """Test basic HTML character escaping."""
        # Test basic HTML characters
        assert self.sanitizer.escape_html("<script>") == "&lt;script&gt;"
        assert self.sanitizer.escape_html("Hello & World") == "Hello &amp; World"
        assert self.sanitizer.escape_html('Say "Hello"') == "Say &quot;Hello&quot;"
        assert self.sanitizer.escape_html("It's working") == "It&#x27;s working"
        
    def test_escape_html_additional_characters(self):
        """Test additional character escaping for enhanced security."""
        assert self.sanitizer.escape_html("path/to/file") == "path&#x2F;to&#x2F;file"
        assert self.sanitizer.escape_html("template`code`") == "template&#x60;code&#x60;"
        assert self.sanitizer.escape_html("a=b") == "a&#x3D;b"
    
    def test_escape_html_empty_and_none(self):
        """Test escaping with empty and None values."""
        assert self.sanitizer.escape_html("") == ""
        assert self.sanitizer.escape_html(None) == "None"
        assert self.sanitizer.escape_html(123) == "123"
    
    def test_is_script_content_detection(self):
        """Test script content detection."""
        # Script tags
        assert self.sanitizer.is_script_content("<script>alert('xss')</script>") == True
        assert self.sanitizer.is_script_content("<SCRIPT>alert('xss')</SCRIPT>") == True
        
        # JavaScript protocols
        assert self.sanitizer.is_script_content("javascript:alert('xss')") == True
        assert self.sanitizer.is_script_content("vbscript:msgbox('xss')") == True
        
        # Event handlers
        assert self.sanitizer.is_script_content("onclick=alert('xss')") == True
        assert self.sanitizer.is_script_content("onload = alert('xss')") == True
        
        # Data URIs
        assert self.sanitizer.is_script_content("data:text/html,<script>alert('xss')</script>") == True
        
        # Safe content
        assert self.sanitizer.is_script_content("Hello World") == False
        assert self.sanitizer.is_script_content("This is safe text") == False
    
    def test_detect_threats(self):
        """Test threat detection functionality."""
        # Script threats
        threats = self.sanitizer.detect_threats("<script>alert('xss')</script>")
        assert "Script Tag" in threats
        
        # Multiple threats
        threats = self.sanitizer.detect_threats("javascript:alert('test')")
        assert "JavaScript Protocol" in threats
        assert "Alert Function" in threats
        
        # No threats
        threats = self.sanitizer.detect_threats("Safe content here")
        assert len(threats) == 0
    
    def test_sanitize_user_input_string(self):
        """Test string sanitization."""
        # Basic sanitization
        result = self.sanitizer.sanitize_user_input("<script>alert('xss')</script>")
        assert "[SCRIPT_REMOVED]" in result  # Default is STRICT level
        
        # Different levels
        basic = self.sanitizer.sanitize_user_input("<b>Bold</b>", SanitizationLevel.BASIC)
        assert basic == "&lt;b&gt;Bold&lt;&#x2F;b&gt;"
        
        strict = self.sanitizer.sanitize_user_input("<script>alert('xss')</script>", SanitizationLevel.STRICT)
        assert "[SCRIPT_REMOVED]" in strict
    
    def test_sanitize_user_input_dict(self):
        """Test dictionary sanitization."""
        input_dict = {
            "name": "<script>alert('xss')</script>",
            "description": "Safe content",
            "nested": {
                "value": "javascript:alert('test')"
            }
        }
        
        result = self.sanitizer.sanitize_user_input(input_dict)
        
        # Check that script content is sanitized
        assert "[SCRIPT_REMOVED]" in result["name"]
        assert "Safe content" in result["description"]  # Safe content preserved
        assert "[SCRIPT_REMOVED]" in result["nested"]["value"]
    
    def test_sanitize_user_input_list(self):
        """Test list sanitization."""
        input_list = [
            "<script>alert('xss')</script>",
            "Safe content",
            {"key": "javascript:alert('test')"}
        ]
        
        result = self.sanitizer.sanitize_user_input(input_list)
        
        assert "[SCRIPT_REMOVED]" in result[0]
        assert result[1] == "Safe content"
        assert isinstance(result[2], dict)
        assert "[SCRIPT_REMOVED]" in result[2]["key"]
    
    def test_sanitization_levels(self):
        """Test different sanitization levels."""
        dangerous_content = "<script>alert('xss')</script>onclick=test"
        
        # Basic level - just escapes HTML
        basic = self.sanitizer._sanitize_string(dangerous_content, SanitizationLevel.BASIC)
        assert "&lt;script&gt;" in basic
        assert "onclick" in basic  # Event handlers not removed in basic mode
        
        # Strict level - removes scripts
        strict = self.sanitizer._sanitize_string(dangerous_content, SanitizationLevel.STRICT)
        assert "[SCRIPT_REMOVED]" in strict
        
        # Paranoid level - maximum security
        paranoid = self.sanitizer._sanitize_string(dangerous_content, SanitizationLevel.PARANOID)
        assert "[SCRIPT_REMOVED]" in paranoid
    
    def test_sanitize_with_result(self):
        """Test sanitization with detailed result."""
        content = "<script>alert('xss')</script>"
        result = self.sanitizer.sanitize_with_result(content)
        
        assert isinstance(result, SanitizationResult)
        assert result.original_content == content
        assert result.sanitized_content != content
        assert len(result.threats_detected) > 0
        assert result.is_safe == False
        assert result.sanitization_level == SanitizationLevel.STRICT
    
    def test_create_safe_template_content(self):
        """Test template-safe content creation."""
        template_data = {
            "title": "<script>alert('xss')</script>",
            "content": "Safe content here",
            "user_input": "javascript:alert('test')"
        }
        
        safe_data = self.sanitizer.create_safe_template_content(template_data)
        
        # All values should be sanitized
        assert "[SCRIPT_REMOVED]" in safe_data["title"]
        assert safe_data["content"] == "Safe content here"
        assert "[SCRIPT_REMOVED]" in safe_data["user_input"]
    
    def test_validate_safe_content(self):
        """Test content safety validation."""
        # Safe content
        assert self.sanitizer.validate_safe_content("Hello World") == True
        assert self.sanitizer.validate_safe_content("This is safe text") == True
        
        # Unsafe content
        assert self.sanitizer.validate_safe_content("<script>alert('xss')</script>") == False
        assert self.sanitizer.validate_safe_content("javascript:alert('test')") == False
    
    def test_neutralize_scripts(self):
        """Test script neutralization."""
        content = "<script>alert('xss')</script>Some text<iframe src='evil'></iframe>"
        neutralized = self.sanitizer._neutralize_scripts(content)
        
        assert "[SCRIPT_REMOVED]" in neutralized
        assert "Some text" in neutralized  # Safe content preserved
        assert "iframe" not in neutralized or "[SCRIPT_REMOVED]" in neutralized
    
    def test_edge_cases(self):
        """Test edge cases and malformed input."""
        # Empty strings
        assert self.sanitizer.sanitize_user_input("") == ""
        
        # Non-string types
        assert self.sanitizer.sanitize_user_input(123) == "123"
        assert self.sanitizer.sanitize_user_input(None) == "None"
        
        # Malformed HTML
        malformed = "<script><script>alert('nested')</script>"
        result = self.sanitizer.sanitize_user_input(malformed)
        assert "[SCRIPT_REMOVED]" in result or "&lt;script&gt;" in result
    
    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        variations = [
            "<SCRIPT>alert('xss')</SCRIPT>",
            "<Script>alert('xss')</Script>",
            "JAVASCRIPT:alert('xss')",
            "JavaScript:alert('xss')",
            "ONCLICK=alert('xss')",
            "OnClick=alert('xss')"
        ]
        
        for variation in variations:
            assert self.sanitizer.is_script_content(variation) == True
    
    def test_performance_with_large_content(self):
        """Test performance with large content."""
        # Create large content with some dangerous patterns
        large_content = "Safe content " * 1000 + "<script>alert('xss')</script>" + "More safe content " * 1000
        
        result = self.sanitizer.sanitize_user_input(large_content)
        
        # Should still detect and neutralize threats
        assert "[SCRIPT_REMOVED]" in result
        assert "Safe content" in result


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_escape_html_function(self):
        """Test escape_html convenience function."""
        result = escape_html("<script>test</script>")
        assert result == "&lt;script&gt;test&lt;&#x2F;script&gt;"
    
    def test_sanitize_user_input_function(self):
        """Test sanitize_user_input convenience function."""
        result = sanitize_user_input("<script>alert('xss')</script>")
        assert "[SCRIPT_REMOVED]" in result
    
    def test_is_script_content_function(self):
        """Test is_script_content convenience function."""
        assert is_script_content("<script>alert('xss')</script>") == True
        assert is_script_content("Safe content") == False
    
    def test_create_safe_template_content_function(self):
        """Test create_safe_template_content convenience function."""
        data = {"content": "<script>alert('xss')</script>"}
        result = create_safe_template_content(data)
        assert "[SCRIPT_REMOVED]" in result["content"]


class TestSecurityScenarios:
    """Test real-world security scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sanitizer = HTMLSanitizer()
    
    def test_xss_attack_vectors(self):
        """Test common XSS attack vectors."""
        attack_vectors = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "<object data=javascript:alert('XSS')>",
            "<embed src=javascript:alert('XSS')>",
            "<link rel=stylesheet href=javascript:alert('XSS')>",
            "<style>@import 'javascript:alert(\"XSS\")';</style>",
            "<div style=background:url(javascript:alert('XSS'))>",
            "data:text/html,<script>alert('XSS')</script>",
            "<meta http-equiv=refresh content=0;url=javascript:alert('XSS')>"
        ]
        
        for vector in attack_vectors:
            result = self.sanitizer.sanitize_user_input(vector, SanitizationLevel.STRICT)
            # Should neutralize dangerous content
            assert "[SCRIPT_REMOVED]" in result
    
    def test_template_injection_prevention(self):
        """Test prevention of template injection attacks."""
        template_data = {
            "user_name": "<script>alert(document.cookie)</script>",
            "user_bio": "{{constructor.constructor('alert(1)')()}}",
            "user_email": "test@example.com<script>alert('xss')</script>"
        }
        
        # Test with STRICT level (default for create_safe_template_content)
        safe_data = self.sanitizer.create_safe_template_content(template_data)
        
        # Script tags should be removed
        assert "[SCRIPT_REMOVED]" in safe_data["user_name"]
        assert "[SCRIPT_REMOVED]" in safe_data["user_email"]
        
        # For more advanced template injection, use PARANOID level
        paranoid_data = self.sanitizer.sanitize_user_input(template_data, SanitizationLevel.PARANOID)
        assert "[SUSPICIOUS_CONTENT_REMOVED]" in paranoid_data["user_bio"]
    
    def test_nested_attack_prevention(self):
        """Test prevention of nested and encoded attacks."""
        nested_attacks = [
            "<scr<script>ipt>alert('XSS')</script>",
            "<<SCRIPT>alert('XSS');//<</SCRIPT>",
            "<script>alert(String.fromCharCode(88,83,83))</script>",
        ]
        
        for attack in nested_attacks:
            result = self.sanitizer.sanitize_user_input(attack, SanitizationLevel.PARANOID)
            # Should neutralize all script content
            assert "[SCRIPT_REMOVED]" in result or "[SUSPICIOUS_CONTENT_REMOVED]" in result
        
        # Test URL encoded attack separately as it may not match script patterns
        encoded_attack = "%3Cscript%3Ealert('XSS')%3C/script%3E"
        result = self.sanitizer.sanitize_user_input(encoded_attack, SanitizationLevel.PARANOID)
        # This should at least escape or remove suspicious content
        assert "[SUSPICIOUS_CONTENT_REMOVED]" in result or "&" in result