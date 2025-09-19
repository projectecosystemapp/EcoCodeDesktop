import { AxiosError } from 'axios';

export enum ErrorType {
  NETWORK = 'network',
  TIMEOUT = 'timeout',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  VALIDATION = 'validation',
  SERVER = 'server',
  CLIENT = 'client',
  UNKNOWN = 'unknown',
}

export enum ErrorSeverity {
  LOW = 'low',
  MEDIUM = 'medium',
  HIGH = 'high',
  CRITICAL = 'critical',
}

export interface ErrorContext {
  operation: string;
  timestamp: Date;
  errorType: ErrorType;
  severity: ErrorSeverity;
  originalError: Error;
  userMessage: string;
  technicalDetails: string;
  recoveryActions: string[];
  retryable: boolean;
}

export interface RetryConfig {
  maxRetries: number;
  baseDelay: number;
  maxDelay: number;
  backoffFactor: number;
  retryableErrors: ErrorType[];
}

export class ErrorHandler {
  private static readonly DEFAULT_RETRY_CONFIG: RetryConfig = {
    maxRetries: 3,
    baseDelay: 1000,
    maxDelay: 10000,
    backoffFactor: 2,
    retryableErrors: [ErrorType.NETWORK, ErrorType.TIMEOUT, ErrorType.SERVER],
  };

  private static readonly USER_FRIENDLY_MESSAGES: Record<ErrorType, string> = {
    [ErrorType.NETWORK]: 'Unable to connect to the server. Please check your internet connection.',
    [ErrorType.TIMEOUT]: 'The request took too long to complete. Please try again.',
    [ErrorType.AUTHENTICATION]: 'Authentication failed. Please check your credentials.',
    [ErrorType.AUTHORIZATION]: 'You do not have permission to perform this action.',
    [ErrorType.VALIDATION]: 'The provided data is invalid. Please check your input.',
    [ErrorType.SERVER]: 'A server error occurred. Please try again later.',
    [ErrorType.CLIENT]: 'A client error occurred. Please check your request.',
    [ErrorType.UNKNOWN]: 'An unexpected error occurred. Please try again.',
  };

  static classifyError(error: Error): ErrorContext {
    const timestamp = new Date();
    let errorType = ErrorType.UNKNOWN;
    let severity = ErrorSeverity.MEDIUM;
    let userMessage = this.USER_FRIENDLY_MESSAGES[ErrorType.UNKNOWN];
    let technicalDetails = error.message;
    let recoveryActions: string[] = ['Try again later'];
    let retryable = false;

    if (error instanceof AxiosError) {
      const status = error.response?.status;
      const code = error.code;

      // Network errors
      if (code === 'ECONNREFUSED' || code === 'ENOTFOUND' || code === 'ENETUNREACH') {
        errorType = ErrorType.NETWORK;
        severity = ErrorSeverity.HIGH;
        userMessage = this.USER_FRIENDLY_MESSAGES[ErrorType.NETWORK];
        recoveryActions = [
          'Check your internet connection',
          'Verify the server is running',
          'Try again in a few moments',
        ];
        retryable = true;
      }
      // Timeout errors
      else if (code === 'ECONNABORTED' || error.message.includes('timeout')) {
        errorType = ErrorType.TIMEOUT;
        severity = ErrorSeverity.MEDIUM;
        userMessage = this.USER_FRIENDLY_MESSAGES[ErrorType.TIMEOUT];
        recoveryActions = ['Try again with a slower connection', 'Reduce request size'];
        retryable = true;
      }
      // HTTP status code errors
      else if (status) {
        if (status === 401) {
          errorType = ErrorType.AUTHENTICATION;
          severity = ErrorSeverity.HIGH;
          userMessage = this.USER_FRIENDLY_MESSAGES[ErrorType.AUTHENTICATION];
          recoveryActions = ['Check your credentials', 'Re-authenticate'];
        } else if (status === 403) {
          errorType = ErrorType.AUTHORIZATION;
          severity = ErrorSeverity.HIGH;
          userMessage = this.USER_FRIENDLY_MESSAGES[ErrorType.AUTHORIZATION];
          recoveryActions = ['Contact an administrator', 'Check your permissions'];
        } else if (status >= 400 && status < 500) {
          errorType = ErrorType.CLIENT;
          severity = ErrorSeverity.MEDIUM;
          userMessage = this.USER_FRIENDLY_MESSAGES[ErrorType.CLIENT];
          recoveryActions = ['Check your input data', 'Verify the request format'];
          
          if (status === 422) {
            errorType = ErrorType.VALIDATION;
            userMessage = this.USER_FRIENDLY_MESSAGES[ErrorType.VALIDATION];
            recoveryActions = ['Check the validation errors', 'Correct the input data'];
          }
        } else if (status >= 500) {
          errorType = ErrorType.SERVER;
          severity = ErrorSeverity.HIGH;
          userMessage = this.USER_FRIENDLY_MESSAGES[ErrorType.SERVER];
          recoveryActions = ['Try again later', 'Contact support if the problem persists'];
          retryable = true;
        }

        // Extract detailed error message from response
        const responseData = error.response?.data;
        if (responseData && typeof responseData === 'object') {
          if ('detail' in responseData && typeof responseData.detail === 'string') {
            technicalDetails = responseData.detail;
          } else if ('message' in responseData && typeof responseData.message === 'string') {
            technicalDetails = responseData.message;
          }
        }
      }
    }

    return {
      operation: 'unknown',
      timestamp,
      errorType,
      severity,
      originalError: error,
      userMessage,
      technicalDetails,
      recoveryActions,
      retryable,
    };
  }

  static async executeWithRetry<T>(
    operation: () => Promise<T>,
    operationName: string,
    config: Partial<RetryConfig> = {},
  ): Promise<T> {
    const retryConfig = { ...this.DEFAULT_RETRY_CONFIG, ...config };
    let lastError: Error;

    for (let attempt = 0; attempt <= retryConfig.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        
        const errorContext = this.classifyError(lastError);
        errorContext.operation = operationName;

        // Don't retry if it's the last attempt or error is not retryable
        if (attempt === retryConfig.maxRetries || !errorContext.retryable) {
          throw this.createEnhancedError(errorContext);
        }

        // Calculate delay with exponential backoff
        const delay = Math.min(
          retryConfig.baseDelay * Math.pow(retryConfig.backoffFactor, attempt),
          retryConfig.maxDelay,
        );

        console.warn(
          `Operation "${operationName}" failed (attempt ${attempt + 1}/${retryConfig.maxRetries + 1}). ` +
          `Retrying in ${delay}ms. Error: ${errorContext.technicalDetails}`,
        );

        await this.sleep(delay);
      }
    }

    // This should never be reached, but TypeScript requires it
    throw this.createEnhancedError(this.classifyError(lastError!));
  }

  static createEnhancedError(context: ErrorContext): Error {
    const error = new Error(context.userMessage);
    
    // Attach additional context to the error object
    Object.assign(error, {
      type: context.errorType,
      severity: context.severity,
      operation: context.operation,
      timestamp: context.timestamp,
      technicalDetails: context.technicalDetails,
      recoveryActions: context.recoveryActions,
      retryable: context.retryable,
      originalError: context.originalError,
    });

    return error;
  }

  private static sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  static logError(context: ErrorContext): void {
    const logLevel = this.getLogLevel(context.severity);
    const logMessage = `[${context.operation}] ${context.errorType.toUpperCase()}: ${context.technicalDetails}`;
    
    console[logLevel](logMessage, {
      timestamp: context.timestamp.toISOString(),
      operation: context.operation,
      type: context.errorType,
      severity: context.severity,
      userMessage: context.userMessage,
      recoveryActions: context.recoveryActions,
      retryable: context.retryable,
      originalError: context.originalError,
    });
  }

  private static getLogLevel(severity: ErrorSeverity): 'error' | 'warn' | 'info' {
    switch (severity) {
      case ErrorSeverity.CRITICAL:
      case ErrorSeverity.HIGH:
        return 'error';
      case ErrorSeverity.MEDIUM:
        return 'warn';
      case ErrorSeverity.LOW:
        return 'info';
      default:
        return 'error';
    }
  }
}