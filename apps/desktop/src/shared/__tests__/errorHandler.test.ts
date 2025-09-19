import { ErrorHandler, ErrorType, ErrorSeverity } from '../errorHandler';
import { AxiosError } from 'axios';

// Mock axios for testing
jest.mock('axios');

describe('ErrorHandler', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Clear any existing timeouts
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('classifyError', () => {
    it('should classify network errors correctly', () => {
      const networkError = new AxiosError('Network Error');
      networkError.code = 'ECONNREFUSED';

      const context = ErrorHandler.classifyError(networkError);

      expect(context.errorType).toBe(ErrorType.NETWORK);
      expect(context.severity).toBe(ErrorSeverity.HIGH);
      expect(context.retryable).toBe(true);
      expect(context.recoveryActions).toContain('Check your internet connection');
    });

    it('should classify timeout errors correctly', () => {
      const timeoutError = new AxiosError('timeout of 5000ms exceeded');
      timeoutError.code = 'ECONNABORTED';

      const context = ErrorHandler.classifyError(timeoutError);

      expect(context.errorType).toBe(ErrorType.TIMEOUT);
      expect(context.severity).toBe(ErrorSeverity.MEDIUM);
      expect(context.retryable).toBe(true);
    });

    it('should classify 401 errors as authentication errors', () => {
      const authError = new AxiosError('Unauthorized');
      authError.response = {
        status: 401,
        data: { detail: 'Invalid credentials' },
      } as any;

      const context = ErrorHandler.classifyError(authError);

      expect(context.errorType).toBe(ErrorType.AUTHENTICATION);
      expect(context.severity).toBe(ErrorSeverity.HIGH);
      expect(context.retryable).toBe(false);
    });

    it('should classify 500 errors as server errors', () => {
      const serverError = new AxiosError('Internal Server Error');
      serverError.response = {
        status: 500,
        data: { detail: 'Database connection failed' },
      } as any;

      const context = ErrorHandler.classifyError(serverError);

      expect(context.errorType).toBe(ErrorType.SERVER);
      expect(context.severity).toBe(ErrorSeverity.HIGH);
      expect(context.retryable).toBe(true);
    });
  });

  describe('executeWithRetry', () => {
    it('should succeed on first attempt', async () => {
      const mockOperation = jest.fn().mockResolvedValue('success');

      const result = await ErrorHandler.executeWithRetry(
        mockOperation,
        'testOperation'
      );

      expect(result).toBe('success');
      expect(mockOperation).toHaveBeenCalledTimes(1);
    });

    it('should retry on retryable errors', async () => {
      const networkError = new AxiosError('Network Error');
      networkError.code = 'ECONNREFUSED';

      const mockOperation = jest
        .fn()
        .mockRejectedValueOnce(networkError)
        .mockRejectedValueOnce(networkError)
        .mockResolvedValue('success');

      // Use real timers for this test to avoid complexity
      jest.useRealTimers();

      const result = await ErrorHandler.executeWithRetry(
        mockOperation,
        'testOperation',
        { maxRetries: 3, baseDelay: 10 } // Very short delay for testing
      );

      expect(result).toBe('success');
      expect(mockOperation).toHaveBeenCalledTimes(3);
      
      // Restore fake timers
      jest.useFakeTimers();
    });

    it('should not retry non-retryable errors', async () => {
      const authError = new AxiosError('Unauthorized');
      authError.response = { status: 401 } as any;

      const mockOperation = jest.fn().mockRejectedValue(authError);

      await expect(
        ErrorHandler.executeWithRetry(mockOperation, 'testOperation')
      ).rejects.toThrow();

      expect(mockOperation).toHaveBeenCalledTimes(1);
    });

    it('should give up after max retries', async () => {
      const networkError = new AxiosError('Network Error');
      networkError.code = 'ECONNREFUSED';

      const mockOperation = jest.fn().mockRejectedValue(networkError);

      // Use real timers for this test
      jest.useRealTimers();

      await expect(
        ErrorHandler.executeWithRetry(
          mockOperation,
          'testOperation',
          { maxRetries: 2, baseDelay: 10 } // Very short delay for testing
        )
      ).rejects.toThrow();
      
      expect(mockOperation).toHaveBeenCalledTimes(3); // Initial + 2 retries
      
      // Restore fake timers
      jest.useFakeTimers();
    });
  });

  describe('createEnhancedError', () => {
    it('should create error with additional context', () => {
      const context = {
        operation: 'testOp',
        timestamp: new Date(),
        errorType: ErrorType.NETWORK,
        severity: ErrorSeverity.HIGH,
        originalError: new Error('Original'),
        userMessage: 'User friendly message',
        technicalDetails: 'Technical details',
        recoveryActions: ['Action 1', 'Action 2'],
        retryable: true,
      };

      const enhancedError = ErrorHandler.createEnhancedError(context);

      expect(enhancedError.message).toBe('User friendly message');
      expect((enhancedError as any).type).toBe(ErrorType.NETWORK);
      expect((enhancedError as any).operation).toBe('testOp');
      expect((enhancedError as any).retryable).toBe(true);
    });
  });
});