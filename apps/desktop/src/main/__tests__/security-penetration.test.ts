/**
 * Comprehensive security penetration tests for desktop application.
 * 
 * Tests URL validation bypass attempts, IPC security, and client-side
 * security measures to ensure the desktop application is secure against
 * various attack vectors.
 * 
 * Requirements addressed:
 * - 1.1, 1.2, 1.3: URL validation bypass attempts
 * - 5.1, 5.2, 5.3, 5.4: Error handling security
 */

import { URLValidator } from '../url-validator';

describe('Security Penetration Tests', () => {
  describe('URL Validation Bypass Attempts', () => {
    test('should block JavaScript protocol variations', () => {
      const maliciousUrls = [
        'javascript:alert("xss")',
        'JAVASCRIPT:alert("xss")',
        'Javascript:alert("xss")',
        'java\x00script:alert("xss")',
        'java\tscript:alert("xss")',
        'java\nscript:alert("xss")',
        'java\rscript:alert("xss")',
        'java script:alert("xss")',
        'javascript\x3Aalert("xss")',
        '&#106;&#97;&#118;&#97;&#115;&#99;&#114;&#105;&#112;&#116;&#58;alert("xss")',
        '%6A%61%76%61%73%63%72%69%70%74%3Aalert("xss")',
        'jAvAsCrIpT:alert("xss")',
        'javascript://comment%0Aalert("xss")',
        'javascript:void(0);alert("xss")',
        'javascript:/**/alert("xss")',
      ];

      maliciousUrls.forEach(url => {
        const result = URLValidator.validateURL(url);
        expect(result.isValid).toBe(false);
        expect(result.securityEvent).toBeDefined();
        expect(result.securityEvent?.severity).toMatch(/high|critical/);
        expect(result.reason).toContain('not allowed');
      });
    });

    test('should block data URI bypass attempts', () => {
      const maliciousDataUris = [
        'data:text/html,<script>alert("xss")</script>',
        'data:text/html;base64,PHNjcmlwdD5hbGVydCgieHNzIik8L3NjcmlwdD4=',
        'DATA:text/html,<script>alert("xss")</script>',
        'data:application/javascript,alert("xss")',
        'data:text/javascript,alert("xss")',
        'data:,<script>alert("xss")</script>',
        'data:text/html;charset=utf-8,<script>alert("xss")</script>',
        'data:image/svg+xml,<svg onload=alert("xss")></svg>',
        'data:text/html;base64,PHNjcmlwdCBzcmM9Imh0dHA6Ly9ldmlsLmNvbS94c3MuanMiPjwvc2NyaXB0Pg==',
      ];

      maliciousDataUris.forEach(url => {
        const result = URLValidator.validateURL(url);
        expect(result.isValid).toBe(false);
        expect(result.securityEvent).toBeDefined();
        expect(result.reason).toContain('not allowed');
      });
    });

    test('should block file protocol traversal attempts', () => {
      const traversalAttempts = [
        'file:///etc/passwd',
        'file:///windows/system32/config/sam',
        'file:///../../../etc/passwd',
        'file:///home/user/../../etc/passwd',
        'file:///C:/Windows/System32/config/SAM',
        'file:///proc/self/environ',
        'file:///dev/mem',
        'file:///var/log/auth.log',
        'file://localhost/etc/passwd',
        'file://127.0.0.1/etc/passwd',
      ];

      traversalAttempts.forEach(url => {
        const result = URLValidator.validateURL(url);
        expect(result.isValid).toBe(false);
        expect(result.securityEvent).toBeDefined();
        expect(result.reason).toContain('not valid');
      });
    });

    test('should block protocol confusion attacks', () => {
      const confusionAttempts = [
        'http://javascript:alert("xss")@example.com',
        'https://data:text/html,<script>alert("xss")</script>@example.com',
        'ftp://javascript:alert("xss")@example.com',
        'mailto:javascript:alert("xss")',
        'tel:javascript:alert("xss")',
        'sms:javascript:alert("xss")',
        'http://example.com#javascript:alert("xss")',
        'https://example.com?redirect=javascript:alert("xss")',
      ];

      confusionAttempts.forEach(url => {
        const result = URLValidator.validateURL(url);
        // Should either be blocked or sanitized safely
        if (result.isValid) {
          // If allowed, ensure it doesn't contain dangerous patterns
          expect(url.toLowerCase()).not.toContain('javascript:');
          expect(url.toLowerCase()).not.toContain('alert(');
        } else {
          expect(result.securityEvent).toBeDefined();
        }
      });
    });

    test('should block Unicode normalization bypass attempts', () => {
      const unicodeAttempts = [
        'javascript\u003Aalert("xss")', // Unicode colon
        'java\u0073cript:alert("xss")', // Unicode 's'
        'javascript\uFF1Aalert("xss")', // Fullwidth colon
        'ｊａｖａｓｃｒｉｐｔ:alert("xss")', // Fullwidth characters
        'javascript\u200D:alert("xss")', // Zero-width joiner
        'java\u200Bscript:alert("xss")', // Zero-width space
      ];

      unicodeAttempts.forEach(url => {
        const result = URLValidator.validateURL(url);
        expect(result.isValid).toBe(false);
        expect(result.securityEvent).toBeDefined();
      });
    });

    test('should handle malformed URLs safely', () => {
      const malformedUrls = [
        '',
        ' ',
        'not-a-url',
        'http://',
        'https://',
        'ftp://[invalid',
        'http://[::1:invalid',
        'javascript:',
        'data:',
        'http://example.com:99999',
        'http://256.256.256.256',
      ];

      malformedUrls.forEach(url => {
        const result = URLValidator.validateURL(url);
        expect(result.isValid).toBe(false);
        if (result.securityEvent) {
          expect(result.securityEvent.eventType).toBe('url_blocked');
        }
      });
    });

    test('should detect suspicious patterns in URLs', () => {
      const suspiciousUrls = [
        'https://example.com?param=<script>alert("xss")</script>',
        'https://example.com#<script>alert("xss")</script>',
        'https://example.com/path?onclick=alert("xss")',
        'https://example.com/path?onload=alert("xss")',
        'https://example.com/path?onerror=alert("xss")',
        'https://example.com/search?q=javascript:alert("xss")',
        'https://example.com/redirect?url=data:text/html,<script>alert("xss")</script>',
        'https://example.com?eval=alert("xss")',
      ];

      suspiciousUrls.forEach(url => {
        const result = URLValidator.validateURL(url);
        expect(result.isValid).toBe(false);
        expect(result.securityEvent).toBeDefined();
        expect(result.securityEvent?.severity).toBe('critical');
        expect(result.reason).toContain('suspicious patterns');
      });
    });

    test('should validate hostnames properly', () => {
      const invalidHostnames = [
        'http://.example.com',
        'http://example..com',
        'http://example.com.',
        'http://-example.com',
        'http://example.com-',
        'http://ex ample.com',
        'http://example.com:',
        'http://[invalid-ipv6',
        'http://256.1.1.1',
      ];

      invalidHostnames.forEach(url => {
        const result = URLValidator.validateURL(url);
        // Some might be caught by URL constructor, others by hostname validation
        if (!result.isValid) {
          expect(result.securityEvent).toBeDefined();
        }
      });
    });

    test('should allow safe URLs', () => {
      const safeUrls = [
        'https://example.com',
        'https://github.com/user/repo',
        'http://localhost:3000',
        'http://127.0.0.1:8080',
        'https://subdomain.example.com/path?param=value',
        'https://example.com:443/secure/path',
        'file:///home/user/documents/safe.pdf',
        'file:///Users/user/Desktop/document.txt',
      ];

      safeUrls.forEach(url => {
        const result = URLValidator.validateURL(url);
        expect(result.isValid).toBe(true);
        expect(result.securityEvent).toBeUndefined();
        expect(result.reason).toBeUndefined();
      });
    });
  });

  describe('Security Event Logging', () => {
    test('should log security events with proper structure', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();

      const maliciousUrl = 'javascript:alert("test")';
      URLValidator.validateURL(maliciousUrl);

      expect(consoleSpy).toHaveBeenCalledWith(
        '[SECURITY EVENT]',
        expect.stringContaining('url_blocked')
      );

      const logCall = consoleSpy.mock.calls[0];
      const logData = JSON.parse(logCall[1]);

      expect(logData).toMatchObject({
        timestamp: expect.any(String),
        level: 'SECURITY',
        event_type: 'url_blocked',
        severity: expect.stringMatching(/low|medium|high|critical/),
        attempted_url: maliciousUrl,
        reason: expect.any(String),
      });

      consoleSpy.mockRestore();
    });

    test('should include security event details in validation result', () => {
      const maliciousUrl = 'javascript:alert("test")';
      const result = URLValidator.validateURL(maliciousUrl);

      expect(result.securityEvent).toMatchObject({
        eventType: 'url_blocked',
        timestamp: expect.any(Date),
        attemptedUrl: maliciousUrl,
        reason: expect.any(String),
        severity: expect.stringMatching(/low|medium|high|critical/),
      });
    });

    test('should handle logging errors gracefully', () => {
      const originalConsole = console.warn;
      console.warn = jest.fn(() => {
        throw new Error('Logging failed');
      });

      // Should not throw even if logging fails
      expect(() => {
        URLValidator.validateURL('javascript:alert("test")');
      }).not.toThrow();

      console.warn = originalConsole;
    });
  });

  describe('Edge Cases and Error Handling', () => {
    test('should handle extremely long URLs', () => {
      const longUrl = 'https://example.com/' + 'a'.repeat(10000);
      const result = URLValidator.validateURL(longUrl);

      // Should handle gracefully without crashing
      expect(typeof result.isValid).toBe('boolean');
      if (result.securityEvent) {
        expect(result.securityEvent.eventType).toBe('url_blocked');
      }
    });

    test('should handle URLs with special characters', () => {
      const specialUrls = [
        'https://example.com/path with spaces',
        'https://example.com/path?param=value with spaces',
        'https://example.com/path#fragment with spaces',
        'https://example.com/path?param=<>&"\'',
        'https://example.com/path?param=%20%21%22%23',
      ];

      specialUrls.forEach(url => {
        const result = URLValidator.validateURL(url);
        expect(typeof result.isValid).toBe('boolean');
        // Should not crash on special characters
      });
    });

    test('should handle null and undefined inputs', () => {
      const invalidInputs = [null, undefined];

      invalidInputs.forEach(input => {
        expect(() => {
          URLValidator.validateURL(input as any);
        }).not.toThrow();
      });
    });

    test('should handle non-string inputs', () => {
      const nonStringInputs = [123, {}, [], true, false];

      nonStringInputs.forEach(input => {
        expect(() => {
          URLValidator.validateURL(input as any);
        }).not.toThrow();
      });
    });
  });

  describe('Performance and DoS Protection', () => {
    test('should handle rapid validation requests', () => {
      const startTime = Date.now();
      const iterations = 1000;

      for (let i = 0; i < iterations; i++) {
        URLValidator.validateURL(`https://example${i}.com`);
      }

      const endTime = Date.now();
      const duration = endTime - startTime;

      // Should complete within reasonable time (adjust threshold as needed)
      expect(duration).toBeLessThan(5000); // 5 seconds for 1000 validations
    });

    test('should handle complex regex patterns efficiently', () => {
      const complexUrls = [
        'https://example.com?' + 'param=value&'.repeat(100),
        'https://example.com/' + 'path/'.repeat(100),
        'https://example.com#' + 'fragment'.repeat(100),
      ];

      complexUrls.forEach(url => {
        const startTime = Date.now();
        const result = URLValidator.validateURL(url);
        const endTime = Date.now();

        expect(typeof result.isValid).toBe('boolean');
        expect(endTime - startTime).toBeLessThan(1000); // Should complete within 1 second
      });
    });

    test('should prevent ReDoS attacks', () => {
      // URLs designed to cause catastrophic backtracking in poorly written regex
      const redosUrls = [
        'https://example.com/' + 'a'.repeat(1000) + '!',
        'https://example.com?' + 'a=b&'.repeat(1000) + '!',
        'javascript:' + '/'.repeat(1000) + 'alert("xss")',
      ];

      redosUrls.forEach(url => {
        const startTime = Date.now();
        const result = URLValidator.validateURL(url);
        const endTime = Date.now();

        expect(typeof result.isValid).toBe('boolean');
        expect(endTime - startTime).toBeLessThan(5000); // Should not hang
      });
    });
  });

  describe('Integration Security Tests', () => {
    test('should maintain security across multiple validation calls', () => {
      const testCases = [
        { url: 'https://safe.com', expected: true },
        { url: 'javascript:alert("xss")', expected: false },
        { url: 'https://another-safe.com', expected: true },
        { url: 'data:text/html,<script>alert("xss")</script>', expected: false },
        { url: 'https://final-safe.com', expected: true },
      ];

      testCases.forEach(({ url, expected }) => {
        const result = URLValidator.validateURL(url);
        expect(result.isValid).toBe(expected);
      });
    });

    test('should not leak information between validation calls', () => {
      // Validate a malicious URL
      const maliciousResult = URLValidator.validateURL('javascript:alert("xss")');
      expect(maliciousResult.isValid).toBe(false);

      // Validate a safe URL - should not be affected by previous validation
      const safeResult = URLValidator.validateURL('https://example.com');
      expect(safeResult.isValid).toBe(true);
      expect(safeResult.securityEvent).toBeUndefined();
    });
  });
});