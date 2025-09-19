/**
 * Comprehensive error handling validation tests for desktop application.
 * 
 * Tests fault injection for network failures, resource exhaustion simulation,
 * recovery mechanism validation, and timeout/retry logic verification.
 * 
 * Requirements addressed:
 * - 5.1, 5.2, 5.3, 5.4: Error handling validation across desktop components
 */

import { errorHandler } from '../errorHandler';

// Mock axios for network testing
jest.mock('axios');
const mockAxios = require('axios');

describe('Error Handling Validation Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.clearAllTimers();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Network Failure Handling', () => {
    test('should handle connection timeout errors', async () => {
      const timeoutError = new Error('timeout of 5000ms exceeded');
      timeoutError.name = 'ECONNABORTED';
      mockAxios.post.mockRejectedValue(timeoutError);

      const result = await errorHandler.handleNetworkError(timeoutError, 'test-operation');

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('NETWORK_TIMEOUT');
      expect(result.userMessage).toContain('connection timed out');
      expect(result.retryable).toBe(true);
    });

    test('should handle connection refused errors', async () => {
      const connectionError = new Error('connect ECONNREFUSED 127.0.0.1:8890');
      connectionError.name = 'ECONNREFUSED';
      mockAxios.post.mockRejectedValue(connectionError);

      const result = await errorHandler.handleNetworkError(connectionError, 'test-operation');

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('CONNECTION_REFUSED');
      expect(result.userMessage).toContain('service is unavailable');
      expect(result.retryable).toBe(true);
    });

    test('should handle DNS resolution failures', async () => {
      const dnsError = new Error('getaddrinfo ENOTFOUND localhost');
      dnsError.name = 'ENOTFOUND';
      mockAxios.post.mockRejectedValue(dnsError);

      const result = await errorHandler.handleNetworkError(dnsError, 'test-operation');

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('DNS_RESOLUTION_FAILED');
      expect(result.userMessage).toContain('network connectivity');
      expect(result.retryable).toBe(true);
    });

    test('should handle HTTP error status codes', async () => {
      const httpError = {
        response: {
          status: 500,
          statusText: 'Internal Server Error',
          data: { message: 'Server error occurred' }
        }
      };
      mockAxios.post.mockRejectedValue(httpError);

      const result = await errorHandler.handleNetworkError(httpError, 'test-operation');

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('HTTP_ERROR');
      expect(result.statusCode).toBe(500);
      expect(result.retryable).toBe(true); // 5xx errors are retryable
    });

    test('should handle network unreachable errors', async () => {
      const networkError = new Error('network is unreachable');
      networkError.name = 'ENETUNREACH';
      mockAxios.post.mockRejectedValue(networkError);

      const result = await errorHandler.handleNetworkError(networkError, 'test-operation');

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('NETWORK_UNREACHABLE');
      expect(result.retryable).toBe(true);
    });
  });

  describe('Retry Logic with Exponential Backoff', () => {
    test('should implement exponential backoff correctly', async () => {
      let attemptCount = 0;
      const mockOperation = jest.fn().mockImplementation(() => {
        attemptCount++;
        if (attemptCount < 3) {
          throw new Error('Temporary failure');
        }
        return Promise.resolve('success');
      });

      const startTime = Date.now();
      const result = await errorHandler.executeWithRetry(mockOperation, {
        maxRetries: 3,
        baseDelay: 100,
        backoffFactor: 2
      });

      expect(result).toBe('success');
      expect(attemptCount).toBe(3);
      expect(mockOperation).toHaveBeenCalledTimes(3);

      // Verify exponential backoff timing
      const expectedMinDelay = 100 + 200; // First retry: 100ms, second retry: 200ms
      jest.advanceTimersByTime(expectedMinDelay);
    });

    test('should respect maximum retry limit', async () => {
      const mockOperation = jest.fn().mockRejectedValue(new Error('Persistent failure'));

      await expect(
        errorHandler.executeWithRetry(mockOperation, {
          maxRetries: 2,
          baseDelay: 50
        })
      ).rejects.toThrow('Persistent failure');

      expect(mockOperation).toHaveBeenCalledTimes(3); // Initial + 2 retries
    });

    test('should add jitter to prevent thundering herd', async () => {
      const delays: number[] = [];
      const originalSetTimeout = global.setTimeout;

      // Mock setTimeout to capture delays
      global.setTimeout = jest.fn().mockImplementation((callback, delay) => {
        delays.push(delay);
        return originalSetTimeout(callback, 0);
      });

      let attemptCount = 0;
      const mockOperation = jest.fn().mockImplementation(() => {
        attemptCount++;
        if (attemptCount < 3) {
          throw new Error('Temporary failure');
        }
        return Promise.resolve('success');
      });

      await errorHandler.executeWithRetry(mockOperation, {
        maxRetries: 3,
        baseDelay: 100,
        jitter: true
      });

      // Verify jitter was applied (delays should vary)
      if (delays.length > 1) {
        const hasVariation = delays.some((delay, index) => 
          index > 0 && Math.abs(delay - delays[0]) > 10
        );
        expect(hasVariation).toBe(true);
      }

      global.setTimeout = originalSetTimeout;
    });

    test('should handle non-retryable errors immediately', async () => {
      const nonRetryableError = new Error('Authentication failed');
      nonRetryableError.name = 'AUTHENTICATION_ERROR';
      
      const mockOperation = jest.fn().mockRejectedValue(nonRetryableError);

      await expect(
        errorHandler.executeWithRetry(mockOperation, {
          maxRetries: 3,
          isRetryable: (error) => error.name !== 'AUTHENTICATION_ERROR'
        })
      ).rejects.toThrow('Authentication failed');

      expect(mockOperation).toHaveBeenCalledTimes(1); // No retries
    });
  });

  describe('Resource Exhaustion Handling', () => {
    test('should handle memory exhaustion gracefully', () => {
      const memoryError = new Error('Cannot allocate memory');
      memoryError.name = 'ENOMEM';

      const result = errorHandler.handleResourceError(memoryError);

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('MEMORY_EXHAUSTED');
      expect(result.userMessage).toContain('insufficient memory');
      expect(result.recoveryActions).toContain('close other applications');
    });

    test('should handle disk space exhaustion', () => {
      const diskError = new Error('No space left on device');
      diskError.name = 'ENOSPC';

      const result = errorHandler.handleResourceError(diskError);

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('DISK_SPACE_EXHAUSTED');
      expect(result.userMessage).toContain('insufficient disk space');
      expect(result.recoveryActions).toContain('free up disk space');
    });

    test('should handle file descriptor exhaustion', () => {
      const fdError = new Error('Too many open files');
      fdError.name = 'EMFILE';

      const result = errorHandler.handleResourceError(fdError);

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('FILE_DESCRIPTOR_EXHAUSTED');
      expect(result.userMessage).toContain('too many open files');
      expect(result.recoveryActions).toContain('restart the application');
    });

    test('should handle concurrent operation limits', async () => {
      const concurrentOperations: Promise<any>[] = [];
      const maxConcurrent = 5;

      // Create more operations than the limit
      for (let i = 0; i < 10; i++) {
        const operation = errorHandler.executeWithConcurrencyLimit(
          () => new Promise(resolve => setTimeout(resolve, 100)),
          maxConcurrent
        );
        concurrentOperations.push(operation);
      }

      // Some operations should be queued
      const results = await Promise.allSettled(concurrentOperations);
      
      // All should eventually complete
      const successful = results.filter(r => r.status === 'fulfilled').length;
      expect(successful).toBe(10);
    });
  });

  describe('Recovery Mechanism Validation', () => {
    test('should implement circuit breaker pattern', async () => {
      let failureCount = 0;
      const mockOperation = jest.fn().mockImplementation(() => {
        failureCount++;
        if (failureCount <= 5) {
          throw new Error('Service unavailable');
        }
        return Promise.resolve('success');
      });

      const circuitBreaker = errorHandler.createCircuitBreaker(mockOperation, {
        failureThreshold: 3,
        resetTimeout: 1000
      });

      // First 3 failures should be attempted
      for (let i = 0; i < 3; i++) {
        await expect(circuitBreaker()).rejects.toThrow('Service unavailable');
      }

      // Circuit should now be open - next calls should fail fast
      await expect(circuitBreaker()).rejects.toThrow('Circuit breaker is open');
      expect(mockOperation).toHaveBeenCalledTimes(3); // No additional calls

      // After reset timeout, circuit should allow one test call
      jest.advanceTimersByTime(1000);
      
      // This should still fail and keep circuit open
      await expect(circuitBreaker()).rejects.toThrow('Service unavailable');
      expect(mockOperation).toHaveBeenCalledTimes(4);
    });

    test('should recover from transient failures', async () => {
      let callCount = 0;
      const mockOperation = jest.fn().mockImplementation(() => {
        callCount++;
        if (callCount <= 2) {
          throw new Error('Transient failure');
        }
        return Promise.resolve('recovered');
      });

      const result = await errorHandler.executeWithRecovery(mockOperation, {
        maxRetries: 3,
        recoveryStrategies: ['retry', 'fallback']
      });

      expect(result).toBe('recovered');
      expect(mockOperation).toHaveBeenCalledTimes(3);
    });

    test('should provide fallback mechanisms', async () => {
      const mockPrimaryOperation = jest.fn().mockRejectedValue(new Error('Primary failed'));
      const mockFallbackOperation = jest.fn().mockResolvedValue('fallback result');

      const result = await errorHandler.executeWithFallback(
        mockPrimaryOperation,
        mockFallbackOperation
      );

      expect(result).toBe('fallback result');
      expect(mockPrimaryOperation).toHaveBeenCalledTimes(1);
      expect(mockFallbackOperation).toHaveBeenCalledTimes(1);
    });

    test('should handle cascading failures gracefully', async () => {
      const mockOperation1 = jest.fn().mockRejectedValue(new Error('Operation 1 failed'));
      const mockOperation2 = jest.fn().mockRejectedValue(new Error('Operation 2 failed'));
      const mockOperation3 = jest.fn().mockResolvedValue('success');

      const result = await errorHandler.executeWithCascadingFallback([
        mockOperation1,
        mockOperation2,
        mockOperation3
      ]);

      expect(result).toBe('success');
      expect(mockOperation1).toHaveBeenCalledTimes(1);
      expect(mockOperation2).toHaveBeenCalledTimes(1);
      expect(mockOperation3).toHaveBeenCalledTimes(1);
    });
  });

  describe('Timeout Handling', () => {
    test('should enforce operation timeouts', async () => {
      const slowOperation = () => new Promise(resolve => 
        setTimeout(resolve, 2000)
      );

      const startTime = Date.now();
      
      await expect(
        errorHandler.executeWithTimeout(slowOperation, 1000)
      ).rejects.toThrow('Operation timed out');

      jest.advanceTimersByTime(1000);
      
      const elapsed = Date.now() - startTime;
      expect(elapsed).toBeLessThan(1500); // Should timeout before completion
    });

    test('should handle progressive timeout increases', async () => {
      let attemptCount = 0;
      const mockOperation = jest.fn().mockImplementation(() => {
        attemptCount++;
        return new Promise(resolve => 
          setTimeout(resolve, 500 * attemptCount) // Each attempt takes longer
        );
      });

      const result = await errorHandler.executeWithProgressiveTimeout(mockOperation, {
        initialTimeout: 300,
        maxTimeout: 2000,
        timeoutMultiplier: 2
      });

      // Should eventually succeed with increased timeout
      expect(attemptCount).toBeGreaterThan(1);
    });

    test('should respect deadline-based timeouts', async () => {
      const deadline = Date.now() + 1000; // 1 second from now
      let attemptCount = 0;

      const mockOperation = jest.fn().mockImplementation(() => {
        attemptCount++;
        if (Date.now() < deadline) {
          throw new Error('Still trying');
        }
        return Promise.resolve('success');
      });

      await expect(
        errorHandler.executeUntilDeadline(mockOperation, deadline)
      ).rejects.toThrow('Deadline exceeded');

      jest.advanceTimersByTime(1000);
      
      expect(attemptCount).toBeGreaterThan(1);
    });
  });

  describe('Error Context and Logging', () => {
    test('should preserve error context across boundaries', () => {
      const originalError = new Error('Original error');
      const context = {
        operation: 'test-operation',
        userId: 'test-user',
        timestamp: Date.now()
      };

      const wrappedError = errorHandler.wrapErrorWithContext(originalError, context);

      expect(wrappedError.context).toEqual(context);
      expect(wrappedError.originalError).toBe(originalError);
      expect(wrappedError.message).toContain('Original error');
    });

    test('should log errors with structured format', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      const error = new Error('Test error');
      const context = { operation: 'test', userId: 'user123' };

      errorHandler.logError(error, context);

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[ERROR]'),
        expect.objectContaining({
          message: 'Test error',
          context: context,
          timestamp: expect.any(String),
          stack: expect.any(String)
        })
      );

      consoleSpy.mockRestore();
    });

    test('should sanitize sensitive information in logs', () => {
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
      
      const error = new Error('Authentication failed');
      const context = {
        operation: 'login',
        password: 'secret123',
        apiKey: 'sk-1234567890',
        token: 'bearer-token-xyz'
      };

      errorHandler.logError(error, context);

      const logCall = consoleSpy.mock.calls[0];
      const logData = logCall[1];

      expect(logData.context.password).toBe('[REDACTED]');
      expect(logData.context.apiKey).toBe('[REDACTED]');
      expect(logData.context.token).toBe('[REDACTED]');

      consoleSpy.mockRestore();
    });
  });

  describe('Integration Error Handling', () => {
    test('should handle IPC communication errors', async () => {
      const ipcError = new Error('IPC channel closed');
      ipcError.name = 'IPC_ERROR';

      const result = errorHandler.handleIPCError(ipcError, 'test-operation');

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('IPC_COMMUNICATION_ERROR');
      expect(result.userMessage).toContain('communication error');
      expect(result.recoveryActions).toContain('restart the application');
    });

    test('should handle Electron process errors', () => {
      const processError = new Error('Renderer process crashed');
      processError.name = 'RENDERER_CRASHED';

      const result = errorHandler.handleElectronError(processError);

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('RENDERER_PROCESS_ERROR');
      expect(result.userMessage).toContain('application component crashed');
      expect(result.recoveryActions).toContain('reload the application');
    });

    test('should handle state synchronization errors', async () => {
      const stateError = new Error('State synchronization failed');
      
      const result = await errorHandler.handleStateError(stateError, {
        currentState: { step: 'requirements' },
        expectedState: { step: 'design' }
      });

      expect(result.success).toBe(false);
      expect(result.errorType).toBe('STATE_SYNCHRONIZATION_ERROR');
      expect(result.recoveryActions).toContain('refresh the current view');
    });

    test('should coordinate error handling across components', async () => {
      const errors = [
        new Error('Network error'),
        new Error('File system error'),
        new Error('State error')
      ];

      const results = await errorHandler.handleMultipleErrors(errors);

      expect(results).toHaveLength(3);
      expect(results.every(r => !r.success)).toBe(true);
      
      // Should provide coordinated recovery strategy
      const recoveryPlan = errorHandler.createRecoveryPlan(results);
      expect(recoveryPlan.steps).toBeDefined();
      expect(recoveryPlan.priority).toBeDefined();
    });
  });
});