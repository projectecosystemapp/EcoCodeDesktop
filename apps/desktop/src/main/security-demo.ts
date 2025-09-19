#!/usr/bin/env node

/**
 * Security Demonstration Script
 * 
 * This script demonstrates the URL validation security fix by testing
 * various URL patterns against the URLValidator.
 */

import { URLValidator } from './url-validator';

console.log('🔒 URL Security Validation Demo\n');

const testUrls = [
  // Valid URLs that should pass
  { url: 'https://github.com/user/repo', expected: true, description: 'Valid HTTPS URL' },
  { url: 'http://localhost:3000', expected: true, description: 'Localhost URL' },
  { url: 'file:///home/user/document.pdf', expected: true, description: 'Valid file URL' },
  
  // Malicious URLs that should be blocked
  { url: 'javascript:alert("xss")', expected: false, description: 'JavaScript injection' },
  { url: 'data:text/html,<script>alert("xss")</script>', expected: false, description: 'Data URL with script' },
  { url: 'vbscript:msgbox("xss")', expected: false, description: 'VBScript injection' },
  { url: 'https://example.com?param=<script>alert("xss")</script>', expected: false, description: 'URL with script tag' },
  { url: 'https://example.com?onclick=alert("xss")', expected: false, description: 'URL with event handler' },
  { url: 'file:///etc/passwd', expected: false, description: 'Sensitive system file' },
  { url: 'file:///home/user/../../etc/passwd', expected: false, description: 'Path traversal attack' },
  
  // Invalid URLs
  { url: 'not-a-valid-url', expected: false, description: 'Invalid URL format' },
  { url: '', expected: false, description: 'Empty URL' },
];

console.log('Testing URL validation...\n');

let passedTests = 0;
let totalTests = testUrls.length;

testUrls.forEach((test, index) => {
  const result = URLValidator.validateURL(test.url);
  const passed = result.isValid === test.expected;
  
  const status = passed ? '✅ PASS' : '❌ FAIL';
  const security = result.securityEvent ? `[${result.securityEvent.severity.toUpperCase()}]` : '';
  
  console.log(`${index + 1}. ${status} ${security} ${test.description}`);
  console.log(`   URL: ${test.url}`);
  console.log(`   Expected: ${test.expected ? 'ALLOW' : 'BLOCK'}, Got: ${result.isValid ? 'ALLOW' : 'BLOCK'}`);
  
  if (!result.isValid && result.reason) {
    console.log(`   Reason: ${result.reason}`);
  }
  
  console.log('');
  
  if (passed) passedTests++;
});

console.log(`\n📊 Test Results: ${passedTests}/${totalTests} tests passed`);

if (passedTests === totalTests) {
  console.log('🎉 All security tests passed! The URL validation is working correctly.');
} else {
  console.log('⚠️  Some tests failed. Please review the URL validation implementation.');
  process.exit(1);
}