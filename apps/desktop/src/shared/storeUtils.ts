export interface LoadingState {
  isLoading: boolean;
  operation: string | null;
  startTime: number | null;
}

export interface ErrorState {
  error: string | null;
  errorType: string | null;
  timestamp: number | null;
  operation: string | null;
  recoveryActions: string[];
}

export interface AsyncOperationConfig {
  timeout?: number;
  retryable?: boolean;
  operation: string;
  onSuccess?: () => void;
  onError?: (error: Error) => void;
  onTimeout?: () => void;
}

export class StoreOperationManager {
  private static readonly DEFAULT_TIMEOUT = 30000; // 30 seconds
  private static readonly OPERATION_TIMEOUTS = new Map<string, NodeJS.Timeout>();

  static createLoadingState(operation: string): LoadingState {
    return {
      isLoading: true,
      operation,
      startTime: Date.now(),
    };
  }

  static createIdleState(): LoadingState {
    return {
      isLoading: false,
      operation: null,
      startTime: null,
    };
  }

  static createErrorState(
    error: Error,
    operation: string,
    recoveryActions: string[] = []
  ): ErrorState {
    return {
      error: error.message,
      errorType: error.constructor.name,
      timestamp: Date.now(),
      operation,
      recoveryActions: recoveryActions.length > 0 ? recoveryActions : ['Try again'],
    };
  }

  static createSuccessState(): ErrorState {
    return {
      error: null,
      errorType: null,
      timestamp: null,
      operation: null,
      recoveryActions: [],
    };
  }

  static async executeWithTimeout<T>(
    operation: () => Promise<T>,
    config: AsyncOperationConfig,
    setState: (state: Partial<{ loading: LoadingState; error: ErrorState }>) => void
  ): Promise<T> {
    const { timeout = this.DEFAULT_TIMEOUT, operation: operationName } = config;
    
    // Clear any existing timeout for this operation
    this.clearOperationTimeout(operationName);
    
    // Set loading state
    setState({
      loading: this.createLoadingState(operationName),
      error: this.createSuccessState(),
    });

    // Create timeout promise
    const timeoutPromise = new Promise<never>((_, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error(`Operation "${operationName}" timed out after ${timeout}ms`));
      }, timeout);
      
      this.OPERATION_TIMEOUTS.set(operationName, timeoutId);
    });

    try {
      // Race between operation and timeout
      const result = await Promise.race([operation(), timeoutPromise]);
      
      // Clear timeout on success
      this.clearOperationTimeout(operationName);
      
      // Set success state
      setState({
        loading: this.createIdleState(),
        error: this.createSuccessState(),
      });
      
      config.onSuccess?.();
      return result;
      
    } catch (error) {
      // Clear timeout on error
      this.clearOperationTimeout(operationName);
      
      const err = error instanceof Error ? error : new Error(String(error));
      
      // Determine recovery actions based on error type
      const recoveryActions = this.getRecoveryActions(err, operationName);
      
      // Set error state
      setState({
        loading: this.createIdleState(),
        error: this.createErrorState(err, operationName, recoveryActions),
      });
      
      if (err.message.includes('timed out')) {
        config.onTimeout?.();
      } else {
        config.onError?.(err);
      }
      
      throw err;
    }
  }

  private static clearOperationTimeout(operation: string): void {
    const timeoutId = this.OPERATION_TIMEOUTS.get(operation);
    if (timeoutId) {
      clearTimeout(timeoutId);
      this.OPERATION_TIMEOUTS.delete(operation);
    }
  }

  private static getRecoveryActions(error: Error, operation: string): string[] {
    const message = error.message.toLowerCase();
    
    if (message.includes('network') || message.includes('connection')) {
      return [
        'Check your internet connection',
        'Verify the server is running',
        'Try again in a few moments',
      ];
    }
    
    if (message.includes('timeout')) {
      return [
        'Check your connection speed',
        'Try again with a more stable connection',
        'Contact support if the problem persists',
      ];
    }
    
    if (message.includes('unauthorized') || message.includes('authentication')) {
      return [
        'Check your credentials',
        'Re-authenticate if necessary',
        'Contact an administrator',
      ];
    }
    
    if (message.includes('validation') || message.includes('invalid')) {
      return [
        'Check your input data',
        'Verify all required fields are filled',
        'Review the validation errors',
      ];
    }
    
    // Default recovery actions
    return [
      'Try the operation again',
      'Refresh the page if the problem persists',
      'Contact support if the issue continues',
    ];
  }

  static cleanup(): void {
    // Clear all pending timeouts
    this.OPERATION_TIMEOUTS.forEach((timeoutId, operation) => {
      clearTimeout(timeoutId);
    });
    this.OPERATION_TIMEOUTS.clear();
  }

  static getOperationDuration(loading: LoadingState): number | null {
    if (!loading.isLoading || !loading.startTime) {
      return null;
    }
    return Date.now() - loading.startTime;
  }

  static isOperationStale(loading: LoadingState, staleThreshold = 60000): boolean {
    const duration = this.getOperationDuration(loading);
    return duration !== null && duration > staleThreshold;
  }
}