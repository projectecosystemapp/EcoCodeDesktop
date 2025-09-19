/**
 * URL validation utility for preventing malicious URL redirection attacks.
 * 
 * This module provides comprehensive URL validation to protect against
 * malicious redirections when opening external URLs.
 * 
 * Requirements addressed:
 * - 1.1: URL validation before calling shell.openExternal()
 * - 1.2: Block invalid or suspicious URLs and log attempts
 * - 1.3: Allow valid URLs to proceed with opening
 */

import { shell } from 'electron';
import { URL } from 'url';

export interface ValidationResult {
  isValid: boolean;
  url?: string;
  errors: string[];
  warnings: string[];
  threatIndicators: string[];
}

export interface SecurityEvent {
  eventId: string;
  eventType: string;
  severity: string;
  timestamp: string;
  blockedContent?: string;
  threatIndicators: string[];
  action: string;
}

export class URLValidator {
  private static readonly ALLOWED_PROTOCOLS = new Set([
    'http:',
    'https:',
    'file:',
    'mailto:',
    'tel:'
  ]);

  private static readonly DANGEROUS_PROTOCOLS = new Set([
    'javascript:',
    'data:',
    'vbscript:',
    'about:',
    'chrome:',
    'chrome-extension:',
    'moz-extension:',
    'ms-browser-extension:'
  ]);

  private static readonly SAFE_DOMAINS = new Set([
    'github.com',
    'stackoverflow.com',
    'developer.mozilla.org',
    'nodejs.org',
    'npmjs.com',
    'microsoft.com',
    'google.com',
    'youtube.com'
  ]);

  private static readonly SUSPICIOUS_PATTERNS = [
    /javascript:/i,
    /data:text\/html/i,
    /data:application\/javascript/i,
    /vbscript:/i,
    /<script/i,
    /onclick=/i,
    /onload=/i,
    /onerror=/i,
    /eval\(/i,
    /alert\(/i,
    /document\./i,
    /window\./i,
    /\.\.\/\.\.\//,  // Path traversal
    /%2e%2e%2f/i,    // URL encoded ../
    /%252e/i,        // Double encoded
    /\x00/,          // Null bytes
    /[<>'"]/         // HTML injection characters
  ];

  private static readonly MAX_URL_LENGTH = 2048;
  private static readonly MAX_DOMAIN_LENGTH = 253;

  /**
   * Validate a URL for security before opening externally.
   * 
   * @param url - URL to validate
   * @returns ValidationResult with validation status and details
   */
  public static validateURL(url: string): ValidationResult {
    const errors: string[] = [];
    const warnings: string[] = [];
    const threatIndicators: string[] = [];

    try {
      // Basic validation
      if (!url || typeof url !== 'string') {
        errors.push('URL is empty or not a string');
        return { isValid: false, errors, warnings, threatIndicators };
      }

      // Check URL length
      if (url.length > this.MAX_URL_LENGTH) {
        errors.push(`URL too long: ${url.length} > ${this.MAX_URL_LENGTH}`);
        return { isValid: false, errors, warnings, threatIndicators };
      }

      // Check for null bytes and control characters
      if (/[\x00-\x1f\x7f]/.test(url)) {
        errors.push('URL contains control characters');
        threatIndicators.push('control_characters');
        return { isValid: false, errors, warnings, threatIndicators };
      }

      // Check for suspicious patterns
      for (const pattern of this.SUSPICIOUS_PATTERNS) {
        if (pattern.test(url)) {
          errors.push(`URL contains suspicious pattern: ${pattern.source}`);
          threatIndicators.push(`suspicious_pattern_${pattern.source}`);
        }
      }

      if (errors.length > 0) {
        return { isValid: false, errors, warnings, threatIndicators };
      }

      // Parse URL
      let parsedUrl: URL;
      try {
        parsedUrl = new URL(url);
      } catch (e) {
        errors.push(`Invalid URL format: ${e instanceof Error ? e.message : 'Unknown error'}`);
        return { isValid: false, errors, warnings, threatIndicators };
      }

      // Validate protocol
      if (this.DANGEROUS_PROTOCOLS.has(parsedUrl.protocol)) {
        errors.push(`Dangerous protocol: ${parsedUrl.protocol}`);
        threatIndicators.push(`dangerous_protocol_${parsedUrl.protocol}`);
        return { isValid: false, errors, warnings, threatIndicators };
      }

      if (!this.ALLOWED_PROTOCOLS.has(parsedUrl.protocol)) {
        errors.push(`Protocol not allowed: ${parsedUrl.protocol}`);
        threatIndicators.push(`disallowed_protocol_${parsedUrl.protocol}`);
        return { isValid: false, errors, warnings, threatIndicators };
      }

      // Validate hostname for http/https URLs
      if (parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:') {
        const hostnameValidation = this.validateHostname(parsedUrl.hostname);
        errors.push(...hostnameValidation.errors);
        warnings.push(...hostnameValidation.warnings);
        threatIndicators.push(...hostnameValidation.threatIndicators);

        if (hostnameValidation.errors.length > 0) {
          return { isValid: false, errors, warnings, threatIndicators };
        }
      }

      // Additional security checks
      const securityCheck = this.performSecurityChecks(parsedUrl);
      warnings.push(...securityCheck.warnings);
      threatIndicators.push(...securityCheck.threatIndicators);

      const isValid = errors.length === 0;
      return {
        isValid,
        url: parsedUrl.toString(),
        errors,
        warnings,
        threatIndicators
      };

    } catch (error) {
      errors.push(`Validation error: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return { isValid: false, errors, warnings, threatIndicators };
    }
  }

  /**
   * Validate hostname for security.
   * 
   * @param hostname - Hostname to validate
   * @returns Validation result for hostname
   */
  private static validateHostname(hostname: string): Pick<ValidationResult, 'errors' | 'warnings' | 'threatIndicators'> {
    const errors: string[] = [];
    const warnings: string[] = [];
    const threatIndicators: string[] = [];

    if (!hostname) {
      errors.push('Empty hostname');
      return { errors, warnings, threatIndicators };
    }

    // Check hostname length
    if (hostname.length > this.MAX_DOMAIN_LENGTH) {
      errors.push(`Hostname too long: ${hostname.length} > ${this.MAX_DOMAIN_LENGTH}`);
      return { errors, warnings, threatIndicators };
    }

    // Check for IP addresses (potentially suspicious)
    if (this.isIPAddress(hostname)) {
      warnings.push('URL uses IP address instead of domain name');
      threatIndicators.push('ip_address_hostname');
    }

    // Check for localhost/internal addresses
    if (this.isLocalAddress(hostname)) {
      warnings.push('URL points to local/internal address');
      threatIndicators.push('local_address');
    }

    // Check for suspicious domain patterns
    if (this.hasSuspiciousDomainPattern(hostname)) {
      warnings.push('Domain has suspicious pattern');
      threatIndicators.push('suspicious_domain_pattern');
    }

    // Check against safe domain list
    if (this.SAFE_DOMAINS.has(hostname.toLowerCase())) {
      // Known safe domain - no additional warnings
    } else {
      warnings.push('Domain not in known safe list');
    }

    return { errors, warnings, threatIndicators };
  }

  /**
   * Check if hostname is an IP address.
   */
  private static isIPAddress(hostname: string): boolean {
    // IPv4 pattern
    const ipv4Pattern = /^(\d{1,3}\.){3}\d{1,3}$/;
    // IPv6 pattern (simplified)
    const ipv6Pattern = /^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$/;
    
    return ipv4Pattern.test(hostname) || ipv6Pattern.test(hostname);
  }

  /**
   * Check if hostname is a local/internal address.
   */
  private static isLocalAddress(hostname: string): boolean {
    const localPatterns = [
      /^localhost$/i,
      /^127\./,
      /^192\.168\./,
      /^10\./,
      /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
      /^::1$/,
      /^fe80:/i,
      /\.local$/i,
      /\.internal$/i
    ];

    return localPatterns.some(pattern => pattern.test(hostname));
  }

  /**
   * Check for suspicious domain patterns.
   */
  private static hasSuspiciousDomainPattern(hostname: string): boolean {
    const suspiciousPatterns = [
      /[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}-[0-9]{1,3}/, // IP-like patterns
      /xn--/i, // Punycode (internationalized domains)
      /[^a-zA-Z0-9.-]/, // Non-standard characters
      /--/, // Double hyphens
      /^\d+$/, // All numeric
      /.{50,}/, // Very long domains
      /(.)\1{4,}/ // Repeated characters
    ];

    return suspiciousPatterns.some(pattern => pattern.test(hostname));
  }

  /**
   * Perform additional security checks on the parsed URL.
   */
  private static performSecurityChecks(url: URL): Pick<ValidationResult, 'warnings' | 'threatIndicators'> {
    const warnings: string[] = [];
    const threatIndicators: string[] = [];

    // Check for suspicious query parameters
    if (url.search) {
      const suspiciousParams = ['javascript', 'script', 'eval', 'onclick', 'onload'];
      const searchLower = url.search.toLowerCase();
      
      for (const param of suspiciousParams) {
        if (searchLower.includes(param)) {
          warnings.push(`Suspicious query parameter: ${param}`);
          threatIndicators.push(`suspicious_query_${param}`);
        }
      }
    }

    // Check for suspicious fragments
    if (url.hash) {
      const hashLower = url.hash.toLowerCase();
      if (hashLower.includes('javascript') || hashLower.includes('script')) {
        warnings.push('Suspicious URL fragment');
        threatIndicators.push('suspicious_fragment');
      }
    }

    // Check for encoded characters that might be used to bypass filters
    const encodedPatterns = [
      /%3c/i, // <
      /%3e/i, // >
      /%22/i, // "
      /%27/i, // '
      /%2f/i  // /
    ];

    const urlString = url.toString();
    for (const pattern of encodedPatterns) {
      if (pattern.test(urlString)) {
        warnings.push('URL contains encoded characters');
        threatIndicators.push('encoded_characters');
        break;
      }
    }

    return { warnings, threatIndicators };
  }

  /**
   * Safely open a URL after validation.
   * 
   * @param url - URL to open
   * @returns Promise that resolves to success status
   */
  public static async safeOpenExternal(url: string): Promise<{ success: boolean; error?: string }> {
    try {
      const validation = this.validateURL(url);
      
      if (!validation.isValid) {
        // Log security event
        const securityEvent: SecurityEvent = {
          eventId: `url_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          eventType: 'url_validation_failure',
          severity: 'medium',
          timestamp: new Date().toISOString(),
          blockedContent: url,
          threatIndicators: validation.threatIndicators,
          action: 'url_validation'
        };

        console.warn('URL validation failed:', {
          url,
          errors: validation.errors,
          threatIndicators: validation.threatIndicators,
          securityEvent
        });

        // In a real implementation, you would send this to your security logging service
        // await this.logSecurityEvent(securityEvent);

        return {
          success: false,
          error: `URL validation failed: ${validation.errors.join(', ')}`
        };
      }

      // Log successful validation with warnings if any
      if (validation.warnings.length > 0) {
        console.info('URL validation passed with warnings:', {
          url: validation.url,
          warnings: validation.warnings,
          threatIndicators: validation.threatIndicators
        });
      }

      // Open the validated URL
      await shell.openExternal(validation.url!);
      
      return { success: true };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('Error opening URL:', { url, error: errorMessage });
      
      return {
        success: false,
        error: `Failed to open URL: ${errorMessage}`
      };
    }
  }

  /**
   * Check if a URL is safe without opening it.
   * 
   * @param url - URL to check
   * @returns Whether the URL is considered safe
   */
  public static isSafeURL(url: string): boolean {
    const validation = this.validateURL(url);
    return validation.isValid;
  }

  /**
   * Get detailed validation information for a URL.
   * 
   * @param url - URL to analyze
   * @returns Detailed validation result
   */
  public static analyzeURL(url: string): ValidationResult {
    return this.validateURL(url);
  }
}

// Export convenience functions
export const validateURL = URLValidator.validateURL.bind(URLValidator);
export const safeOpenExternal = URLValidator.safeOpenExternal.bind(URLValidator);
export const isSafeURL = URLValidator.isSafeURL.bind(URLValidator);
export const analyzeURL = URLValidator.analyzeURL.bind(URLValidator);