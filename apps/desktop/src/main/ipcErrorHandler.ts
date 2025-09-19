import { ErrorHandler, ErrorContext, ErrorType, ErrorSeverity } from '../shared/errorHandler';

export interface IPCErrorContext extends ErrorContext {
  ipcChannel: string;
  args: any[];
}

export class IPCErrorHandler {
  static handleIPCError(
    error: Error,
    channel: string,
    args: any[] = [],
    fallbackValue?: any
  ): never | any {
    const errorContext = ErrorHandler.classifyError(error);
    
    const ipcContext: IPCErrorContext = {
      ...errorContext,
      operation: `IPC:${channel}`,
      ipcChannel: channel,
      args,
    };

    // Log the error with IPC-specific context
    this.logIPCError(ipcContext);

    // If a fallback value is provided and the error is not critical, return it
    if (fallbackValue !== undefined && errorContext.severity !== ErrorSeverity.CRITICAL) {
      console.warn(`IPC operation "${channel}" failed, returning fallback value:`, fallbackValue);
      return fallbackValue;
    }

    // Create enhanced error with IPC context
    const enhancedError = ErrorHandler.createEnhancedError(ipcContext);
    
    // Add IPC-specific properties
    Object.assign(enhancedError, {
      ipcChannel: channel,
      args,
    });

    throw enhancedError;
  }

  static async executeIPCWithFallback<T>(
    operation: () => Promise<T>,
    channel: string,
    args: any[] = [],
    fallbackValue?: T
  ): Promise<T> {
    try {
      return await operation();
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      
      if (fallbackValue !== undefined) {
        return this.handleIPCError(err, channel, args, fallbackValue);
      }
      
      return this.handleIPCError(err, channel, args);
    }
  }

  static createSafeIPCHandler<T extends any[], R>(
    handler: (...args: T) => Promise<R>,
    channel: string,
    fallbackValue?: R
  ) {
    return async (_event: any, ...args: T): Promise<R> => {
      return this.executeIPCWithFallback(
        () => handler(...args),
        channel,
        args,
        fallbackValue
      );
    };
  }

  private static logIPCError(context: IPCErrorContext): void {
    const logLevel = this.getLogLevel(context.severity);
    const logMessage = `[IPC:${context.ipcChannel}] ${context.errorType.toUpperCase()}: ${context.technicalDetails}`;
    
    console[logLevel](logMessage, {
      timestamp: context.timestamp.toISOString(),
      ipcChannel: context.ipcChannel,
      operation: context.operation,
      type: context.errorType,
      severity: context.severity,
      userMessage: context.userMessage,
      recoveryActions: context.recoveryActions,
      retryable: context.retryable,
      args: context.args,
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

  static getDefaultFallbacks() {
    return {
      health: { status: 'unknown', version: 'unknown', timestamp: new Date().toISOString() },
      projects: [],
      specs: [],
      progress: {
        spec_id: '',
        total_tasks: 0,
        completed_tasks: 0,
        in_progress_tasks: 0,
        not_started_tasks: 0,
        blocked_tasks: 0,
        progress_percentage: 0,
        current_phase: 'requirements',
        status: 'unknown',
      },
    };
  }
}