import { URL } from 'node:url';

export interface ValidationResult {
  isValid: boolean;
  reason?: string;
  securityEvent?: SecurityEvent;
}

export interface SecurityEvent {
  eventType: 'url_blocked';
  timestamp: Date;
  attemptedUrl: string;
  reason: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export class URLValidator {
  private static readonly ALLOWED_PROTOCOLS = new Set(['http:', 'https:', 'file:']);
  private static readonly BLOCKED_PROTOCOLS = new Set([
    'javascript:',
    'data:',
    'vbscript:',
    'about:',
    'chrome:',
    'chrome-extension:',
    'moz-extension:',
    'ms-browser-extension:',
  ]);

  private static readonly SAFE_DOMAIN_PATTERNS = [
    /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/,
  ];

  private static readonly SUSPICIOUS_PATTERNS = [
    /javascript:/i,
    /data:/i,
    /vbscript:/i,
    /<script/i,
    /onload=/i,
    /onerror=/i,
    /onclick=/i,
  ];

  /**
   * Validates a URL for security before allowing external opening
   */
  public static validateURL(url: string): ValidationResult {
    try {
      // Basic URL format validation
      const parsedUrl = new URL(url);

      // Check protocol allowlist
      if (!this.isAllowedProtocol(parsedUrl.protocol)) {
        const securityEvent: SecurityEvent = {
          eventType: 'url_blocked',
          timestamp: new Date(),
          attemptedUrl: url,
          reason: `Blocked protocol: ${parsedUrl.protocol}`,
          severity: 'high',
        };

        this.logSecurityEvent(securityEvent);

        return {
          isValid: false,
          reason: `Protocol ${parsedUrl.protocol} is not allowed`,
          securityEvent,
        };
      }

      // Check for suspicious patterns in the entire URL
      if (this.containsSuspiciousPatterns(url)) {
        const securityEvent: SecurityEvent = {
          eventType: 'url_blocked',
          timestamp: new Date(),
          attemptedUrl: url,
          reason: 'Contains suspicious patterns',
          severity: 'critical',
        };

        this.logSecurityEvent(securityEvent);

        return {
          isValid: false,
          reason: 'URL contains suspicious patterns',
          securityEvent,
        };
      }

      // Validate hostname for http/https URLs
      if (parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:') {
        if (!this.isSafeHost(parsedUrl.hostname)) {
          const securityEvent: SecurityEvent = {
            eventType: 'url_blocked',
            timestamp: new Date(),
            attemptedUrl: url,
            reason: `Invalid hostname: ${parsedUrl.hostname}`,
            severity: 'medium',
          };

          this.logSecurityEvent(securityEvent);

          return {
            isValid: false,
            reason: `Hostname ${parsedUrl.hostname} is not valid`,
            securityEvent,
          };
        }
      }

      // Additional validation for file URLs
      if (parsedUrl.protocol === 'file:') {
        if (!this.isValidFileUrl(parsedUrl)) {
          const securityEvent: SecurityEvent = {
            eventType: 'url_blocked',
            timestamp: new Date(),
            attemptedUrl: url,
            reason: 'Invalid file URL',
            severity: 'high',
          };

          this.logSecurityEvent(securityEvent);

          return {
            isValid: false,
            reason: 'File URL is not valid',
            securityEvent,
          };
        }
      }

      return { isValid: true };
    } catch (error) {
      const securityEvent: SecurityEvent = {
        eventType: 'url_blocked',
        timestamp: new Date(),
        attemptedUrl: url,
        reason: `Invalid URL format: ${error instanceof Error ? error.message : 'Unknown error'}`,
        severity: 'medium',
      };

      this.logSecurityEvent(securityEvent);

      return {
        isValid: false,
        reason: 'Invalid URL format',
        securityEvent,
      };
    }
  }

  /**
   * Checks if the protocol is in the allowlist
   */
  private static isAllowedProtocol(protocol: string): boolean {
    return this.ALLOWED_PROTOCOLS.has(protocol.toLowerCase());
  }

  /**
   * Validates hostname against safe domain patterns
   */
  private static isSafeHost(hostname: string): boolean {
    if (!hostname) return false;

    // Check for localhost and IP addresses (basic validation)
    if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1') {
      return true;
    }

    // Validate against domain patterns
    return this.SAFE_DOMAIN_PATTERNS.some(pattern => pattern.test(hostname));
  }

  /**
   * Checks for suspicious patterns that might indicate XSS or other attacks
   */
  private static containsSuspiciousPatterns(url: string): boolean {
    return this.SUSPICIOUS_PATTERNS.some(pattern => pattern.test(url));
  }

  /**
   * Validates file URLs for basic security
   */
  private static isValidFileUrl(parsedUrl: URL): boolean {
    // Basic validation - ensure it's a proper file URL
    // Additional restrictions can be added based on security requirements
    const pathname = parsedUrl.pathname;
    
    // Block access to sensitive system files
    const sensitivePatterns = [
      /\/etc\/passwd/i,
      /\/etc\/shadow/i,
      /\/windows\/system32/i,
      /\.\.\/\.\.\//,  // Path traversal
    ];

    return !sensitivePatterns.some(pattern => pattern.test(pathname));
  }

  /**
   * Logs security events for monitoring and analysis
   */
  private static logSecurityEvent(event: SecurityEvent): void {
    const logEntry = {
      timestamp: event.timestamp.toISOString(),
      level: 'SECURITY',
      event_type: event.eventType,
      severity: event.severity,
      attempted_url: event.attemptedUrl,
      reason: event.reason,
    };

    // Log to console with structured format
    console.warn('[SECURITY EVENT]', JSON.stringify(logEntry, null, 2));

    // In a production environment, this could also:
    // - Write to a dedicated security log file
    // - Send to a security monitoring service
    // - Trigger alerts for critical events
  }
}