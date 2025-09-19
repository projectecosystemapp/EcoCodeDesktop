import { URLValidator } from '../url-validator';

describe('URLValidator', () => {
  describe('validateURL', () => {
    it('should allow valid HTTP URLs', () => {
      const result = URLValidator.validateURL('https://example.com');
      expect(result.isValid).toBe(true);
      expect(result.reason).toBeUndefined();
    });

    it('should allow valid HTTPS URLs', () => {
      const result = URLValidator.validateURL('https://github.com/user/repo');
      expect(result.isValid).toBe(true);
      expect(result.reason).toBeUndefined();
    });

    it('should allow localhost URLs', () => {
      const result = URLValidator.validateURL('http://localhost:3000');
      expect(result.isValid).toBe(true);
      expect(result.reason).toBeUndefined();
    });

    it('should allow valid file URLs', () => {
      const result = URLValidator.validateURL('file:///home/user/document.pdf');
      expect(result.isValid).toBe(true);
      expect(result.reason).toBeUndefined();
    });

    it('should block javascript: URLs', () => {
      const result = URLValidator.validateURL('javascript:alert("xss")');
      expect(result.isValid).toBe(false);
      expect(result.reason).toContain('Protocol javascript: is not allowed');
      expect(result.securityEvent?.severity).toBe('high');
    });

    it('should block data: URLs', () => {
      const result = URLValidator.validateURL('data:text/html,<script>alert("xss")</script>');
      expect(result.isValid).toBe(false);
      expect(result.reason).toContain('Protocol data: is not allowed');
      expect(result.securityEvent?.severity).toBe('high');
    });

    it('should block vbscript: URLs', () => {
      const result = URLValidator.validateURL('vbscript:msgbox("xss")');
      expect(result.isValid).toBe(false);
      expect(result.reason).toContain('Protocol vbscript: is not allowed');
    });

    it('should block URLs with suspicious patterns', () => {
      const result = URLValidator.validateURL('https://example.com?param=<script>alert("xss")</script>');
      expect(result.isValid).toBe(false);
      expect(result.reason).toContain('suspicious patterns');
      expect(result.securityEvent?.severity).toBe('critical');
    });

    it('should block URLs with onclick handlers', () => {
      const result = URLValidator.validateURL('https://example.com?onclick=alert("xss")');
      expect(result.isValid).toBe(false);
      expect(result.reason).toContain('suspicious patterns');
    });

    it('should block file URLs accessing sensitive system files', () => {
      const result = URLValidator.validateURL('file:///etc/passwd');
      expect(result.isValid).toBe(false);
      expect(result.reason).toContain('File URL is not valid');
    });

    it('should block file URLs with path traversal', () => {
      const result = URLValidator.validateURL('file:///home/user/../../etc/passwd');
      expect(result.isValid).toBe(false);
      expect(result.reason).toContain('File URL is not valid');
    });

    it('should handle invalid URL formats', () => {
      const result = URLValidator.validateURL('not-a-valid-url');
      expect(result.isValid).toBe(false);
      expect(result.reason).toContain('Invalid URL format');
    });

    it('should handle empty URLs', () => {
      const result = URLValidator.validateURL('');
      expect(result.isValid).toBe(false);
      expect(result.reason).toContain('Invalid URL format');
    });

    it('should log security events for blocked URLs', () => {
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();
      
      URLValidator.validateURL('javascript:alert("test")');
      
      expect(consoleSpy).toHaveBeenCalledWith(
        '[SECURITY EVENT]',
        expect.stringContaining('url_blocked')
      );
      
      consoleSpy.mockRestore();
    });

    it('should include proper security event details', () => {
      const result = URLValidator.validateURL('javascript:alert("test")');
      
      expect(result.securityEvent).toBeDefined();
      expect(result.securityEvent?.eventType).toBe('url_blocked');
      expect(result.securityEvent?.attemptedUrl).toBe('javascript:alert("test")');
      expect(result.securityEvent?.timestamp).toBeInstanceOf(Date);
      expect(result.securityEvent?.severity).toBe('high');
    });
  });
});