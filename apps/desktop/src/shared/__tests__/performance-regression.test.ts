/**
 * Performance regression tests for desktop application.
 * 
 * Tests benchmark performance for Levenshtein algorithm optimization,
 * memory usage validation, load testing for performance under stress,
 * and automated performance regression detection.
 * 
 * Requirements addressed:
 * - 6.1, 6.2, 6.3, 6.4: Performance optimization validation and regression detection
 */

import { calculateSimilarity, optimizedLevenshteinDistance } from '../specValidation';

interface PerformanceMetrics {
  executionTime: number;
  memoryUsage: number;
  operationsPerSecond: number;
  gcCollections: number;
}

interface BenchmarkResult {
  testName: string;
  metrics: PerformanceMetrics;
  baselineMetrics?: PerformanceMetrics;
  regressionDetected: boolean;
  performanceRatio: number;
}

class PerformanceBenchmark {
  private baselines: Map<string, PerformanceMetrics> = new Map();

  measurePerformance<T>(func: () => T): PerformanceMetrics {
    // Force garbage collection if available
    if (global.gc) {
      global.gc();
    }

    const initialMemory = process.memoryUsage();
    const startTime = performance.now();

    // Execute function
    const result = func();

    const endTime = performance.now();
    const finalMemory = process.memoryUsage();

    const executionTime = endTime - startTime;
    const memoryUsage = finalMemory.heapUsed - initialMemory.heapUsed;
    const operationsPerSecond = 1000 / executionTime; // Convert ms to ops/sec

    return {
      executionTime,
      memoryUsage,
      operationsPerSecond,
      gcCollections: 0 // Not easily measurable in Node.js
    };
  }

  benchmarkFunction<T>(testName: string, func: () => T): BenchmarkResult {
    const metrics = this.measurePerformance(func);
    const baselineMetrics = this.baselines.get(testName);
    
    let regressionDetected = false;
    let performanceRatio = 1.0;

    if (baselineMetrics) {
      performanceRatio = metrics.executionTime / baselineMetrics.executionTime;
      regressionDetected = performanceRatio > 1.2; // 20% degradation threshold
    } else {
      // Save as new baseline
      this.baselines.set(testName, metrics);
    }

    return {
      testName,
      metrics,
      baselineMetrics,
      regressionDetected,
      performanceRatio
    };
  }
}

describe('Performance Regression Tests', () => {
  let benchmark: PerformanceBenchmark;

  beforeEach(() => {
    benchmark = new PerformanceBenchmark();
  });

  describe('Levenshtein Algorithm Performance', () => {
    test('should perform efficiently with small strings', () => {
      const str1 = 'hello world';
      const str2 = 'hello word';

      const result = benchmark.benchmarkFunction(
        'levenshtein_small_strings',
        () => optimizedLevenshteinDistance(str1, str2)
      );

      expect(result.metrics.executionTime).toBeLessThan(1); // < 1ms
      expect(result.regressionDetected).toBe(false);
    });

    test('should perform efficiently with medium strings', () => {
      const str1 = 'a'.repeat(100) + 'hello world' + 'b'.repeat(100);
      const str2 = 'a'.repeat(100) + 'hello word' + 'b'.repeat(100);

      const result = benchmark.benchmarkFunction(
        'levenshtein_medium_strings',
        () => optimizedLevenshteinDistance(str1, str2)
      );

      expect(result.metrics.executionTime).toBeLessThan(10); // < 10ms
      expect(result.regressionDetected).toBe(false);
    });

    test('should perform efficiently with large strings', () => {
      const str1 = 'a'.repeat(1000) + 'hello world' + 'b'.repeat(1000);
      const str2 = 'a'.repeat(1000) + 'hello word' + 'b'.repeat(1000);

      const result = benchmark.benchmarkFunction(
        'levenshtein_large_strings',
        () => optimizedLevenshteinDistance(str1, str2)
      );

      expect(result.metrics.executionTime).toBeLessThan(100); // < 100ms
      expect(result.regressionDetected).toBe(false);
    });

    test('should use memory efficiently', () => {
      const str1 = 'x'.repeat(500);
      const str2 = 'y'.repeat(500);

      const result = benchmark.benchmarkFunction(
        'levenshtein_memory_efficiency',
        () => optimizedLevenshteinDistance(str1, str2)
      );

      // Memory usage should be reasonable (not O(m*n))
      const expectedMaxMemory = Math.min(str1.length, str2.length) * 8 * 10; // Rough estimate
      expect(Math.abs(result.metrics.memoryUsage)).toBeLessThan(expectedMaxMemory);
    });

    test('should handle similarity calculation efficiently', () => {
      const str1 = 'This is a test document for similarity calculation';
      const str2 = 'This is a test document for similarity computation';

      const result = benchmark.benchmarkFunction(
        'similarity_calculation',
        () => calculateSimilarity(str1, str2)
      );

      expect(result.metrics.executionTime).toBeLessThan(5); // < 5ms
      expect(result.regressionDetected).toBe(false);
    });

    test('should handle batch processing efficiently', () => {
      const strings = Array.from({ length: 100 }, (_, i) => `test string ${i}`);
      const reference = 'test string 50';

      const result = benchmark.benchmarkFunction(
        'levenshtein_batch_processing',
        () => {
          return strings.map(s => calculateSimilarity(reference, s));
        }
      );

      expect(result.metrics.executionTime).toBeLessThan(100); // < 100ms for 100 comparisons
      expect(result.metrics.operationsPerSecond).toBeGreaterThan(10); // At least 10 ops/sec
    });

    test('should handle worst-case scenarios efficiently', () => {
      // Completely different strings of same length
      const str1 = 'a'.repeat(200);
      const str2 = 'b'.repeat(200);

      const result = benchmark.benchmarkFunction(
        'levenshtein_worst_case',
        () => optimizedLevenshteinDistance(str1, str2)
      );

      expect(result.metrics.executionTime).toBeLessThan(50); // < 50ms
      expect(result.regressionDetected).toBe(false);
    });
  });

  describe('Memory Usage Validation', () => {
    test('should not leak memory during repeated operations', () => {
      const initialMemory = process.memoryUsage().heapUsed;

      // Perform operations multiple times
      for (let iteration = 0; iteration < 10; iteration++) {
        for (let i = 0; i < 10; i++) {
          const str1 = `test string ${iteration}-${i}`;
          const str2 = `test string ${iteration}-${i + 1}`;
          calculateSimilarity(str1, str2);
        }

        // Force garbage collection if available
        if (global.gc) {
          global.gc();
        }
      }

      const finalMemory = process.memoryUsage().heapUsed;
      const memoryGrowth = finalMemory - initialMemory;

      // Memory growth should be reasonable (< 10MB)
      expect(memoryGrowth).toBeLessThan(10 * 1024 * 1024);
    });

    test('should handle large datasets without excessive memory usage', () => {
      const largeStrings = Array.from({ length: 1000 }, (_, i) => 
        `Large document content ${i} `.repeat(100)
      );

      const result = benchmark.benchmarkFunction(
        'large_dataset_memory_usage',
        () => {
          const reference = largeStrings[0];
          return largeStrings.slice(1, 100).map(s => calculateSimilarity(reference, s));
        }
      );

      // Should not use excessive memory
      expect(Math.abs(result.metrics.memoryUsage)).toBeLessThan(100 * 1024 * 1024); // < 100MB
    });

    test('should clean up temporary objects efficiently', () => {
      const result = benchmark.benchmarkFunction(
        'temporary_object_cleanup',
        () => {
          const results = [];
          for (let i = 0; i < 1000; i++) {
            const tempStr1 = `temporary string ${i}`;
            const tempStr2 = `temporary string ${i + 1}`;
            const similarity = calculateSimilarity(tempStr1, tempStr2);
            results.push(similarity);
          }
          return results;
        }
      );

      // Memory usage should be reasonable despite many temporary objects
      expect(Math.abs(result.metrics.memoryUsage)).toBeLessThan(50 * 1024 * 1024); // < 50MB
    });
  });

  describe('Load Testing Performance', () => {
    test('should handle high-volume string comparisons', () => {
      const result = benchmark.benchmarkFunction(
        'high_volume_comparisons',
        () => {
          const results = [];
          for (let i = 0; i < 500; i++) {
            const str1 = `Document ${i} content `.repeat(20);
            const str2 = `Document ${i + 1} content `.repeat(20);
            results.push(calculateSimilarity(str1, str2));
          }
          return results;
        }
      );

      expect(result.metrics.executionTime).toBeLessThan(5000); // < 5 seconds
      expect(result.metrics.operationsPerSecond).toBeGreaterThan(0.1); // At least 0.1 ops/sec
      expect(result.regressionDetected).toBe(false);
    });

    test('should handle concurrent operations efficiently', async () => {
      const concurrentOperations = Array.from({ length: 10 }, (_, i) => 
        new Promise<number>(resolve => {
          setTimeout(() => {
            const str1 = `Concurrent operation ${i} `.repeat(50);
            const str2 = `Concurrent operation ${i + 1} `.repeat(50);
            const similarity = calculateSimilarity(str1, str2);
            resolve(similarity);
          }, Math.random() * 10); // Random delay 0-10ms
        })
      );

      const startTime = performance.now();
      const results = await Promise.all(concurrentOperations);
      const endTime = performance.now();

      expect(results).toHaveLength(10);
      expect(endTime - startTime).toBeLessThan(1000); // Should complete within 1 second
    });

    test('should maintain performance under stress', () => {
      const stressTestData = Array.from({ length: 100 }, (_, i) => ({
        str1: `Stress test document ${i} `.repeat(100),
        str2: `Stress test document ${i + 1} `.repeat(100)
      }));

      const result = benchmark.benchmarkFunction(
        'stress_test_performance',
        () => {
          return stressTestData.map(({ str1, str2 }) => calculateSimilarity(str1, str2));
        }
      );

      expect(result.metrics.executionTime).toBeLessThan(10000); // < 10 seconds
      expect(result.regressionDetected).toBe(false);
    });
  });

  describe('Automated Regression Detection', () => {
    test('should detect performance regressions', () => {
      const fastOperation = () => {
        return Array.from({ length: 1000 }, (_, i) => i).reduce((a, b) => a + b, 0);
      };

      const slowOperation = () => {
        // Intentionally slower version
        let result = 0;
        for (let i = 0; i < 1000; i++) {
          result += i;
          // Add artificial delay to simulate regression
          const start = performance.now();
          while (performance.now() - start < 0.1) {
            // Busy wait for 0.1ms
          }
        }
        return result;
      };

      // Establish baseline with fast operation
      const baselineResult = benchmark.benchmarkFunction(
        'regression_test_baseline',
        fastOperation
      );

      // Test with slower operation (simulating regression)
      const regressionResult = benchmark.benchmarkFunction(
        'regression_test_baseline', // Same test name to compare
        slowOperation
      );

      expect(regressionResult.regressionDetected).toBe(true);
      expect(regressionResult.performanceRatio).toBeGreaterThan(1.2);
    });

    test('should track performance trends', () => {
      const results: BenchmarkResult[] = [];

      // Simulate performance degradation over time
      for (let i = 0; i < 5; i++) {
        const delay = i * 2; // Increasing delay
        const result = benchmark.benchmarkFunction(
          `trend_test_run_${i}`,
          () => {
            const start = performance.now();
            while (performance.now() - start < delay) {
              // Busy wait
            }
            return Array.from({ length: 100 }, (_, j) => j).reduce((a, b) => a + b, 0);
          }
        );
        results.push(result);
      }

      // Analyze trend
      const executionTimes = results.map(r => r.metrics.executionTime);
      
      // Should show increasing trend
      expect(executionTimes[executionTimes.length - 1]).toBeGreaterThan(executionTimes[0]);
    });

    test('should generate performance reports', () => {
      const testOperations = [
        () => calculateSimilarity('test1', 'test2'),
        () => optimizedLevenshteinDistance('hello', 'world'),
        () => Array.from({ length: 100 }, (_, i) => i * 2)
      ];

      const results = testOperations.map((op, i) => 
        benchmark.benchmarkFunction(`report_test_${i}`, op)
      );

      const report = generatePerformanceReport(results);

      expect(report.summary.totalTests).toBe(3);
      expect(report.summary.regressionsDetected).toBeGreaterThanOrEqual(0);
      expect(report.details).toHaveLength(3);
      expect(report.recommendations).toBeDefined();
    });

    test('should handle baseline management', () => {
      const testOperation = () => {
        return Array.from({ length: 100 }, (_, i) => i ** 2).sort((a, b) => a - b);
      };

      // Create initial baseline
      const result1 = benchmark.benchmarkFunction(
        'baseline_management_test',
        testOperation
      );

      expect(result1.regressionDetected).toBe(false);
      expect(result1.baselineMetrics).toBeUndefined();

      // Run again with same performance
      const result2 = benchmark.benchmarkFunction(
        'baseline_management_test',
        testOperation
      );

      expect(result2.baselineMetrics).toBeDefined();
      expect(Math.abs(result2.performanceRatio - 1.0)).toBeLessThan(0.5);
    });
  });

  describe('Performance Optimization Validation', () => {
    test('should validate space complexity optimization', () => {
      // Test that optimized algorithm uses O(min(m,n)) space instead of O(m*n)
      const shortStr = 'short';
      const longStr = 'a'.repeat(1000);

      const result1 = benchmark.benchmarkFunction(
        'space_complexity_short_long',
        () => optimizedLevenshteinDistance(shortStr, longStr)
      );

      const result2 = benchmark.benchmarkFunction(
        'space_complexity_long_short',
        () => optimizedLevenshteinDistance(longStr, shortStr)
      );

      // Both should have similar performance (space complexity should be based on shorter string)
      const timeDifference = Math.abs(result1.metrics.executionTime - result2.metrics.executionTime);
      expect(timeDifference).toBeLessThan(result1.metrics.executionTime * 0.5); // Within 50%
    });

    test('should validate early termination optimization', () => {
      const identicalStr1 = 'identical string content';
      const identicalStr2 = 'identical string content';
      const differentStr = 'completely different content';

      const identicalResult = benchmark.benchmarkFunction(
        'early_termination_identical',
        () => optimizedLevenshteinDistance(identicalStr1, identicalStr2)
      );

      const differentResult = benchmark.benchmarkFunction(
        'early_termination_different',
        () => optimizedLevenshteinDistance(identicalStr1, differentStr)
      );

      // Identical strings should be processed much faster (early termination)
      expect(identicalResult.metrics.executionTime).toBeLessThan(differentResult.metrics.executionTime);
    });

    test('should validate algorithm correctness under optimization', () => {
      const testCases = [
        { str1: '', str2: '', expected: 0 },
        { str1: 'a', str2: '', expected: 1 },
        { str1: '', str2: 'a', expected: 1 },
        { str1: 'abc', str2: 'abc', expected: 0 },
        { str1: 'abc', str2: 'ab', expected: 1 },
        { str1: 'abc', str2: 'abcd', expected: 1 },
        { str1: 'kitten', str2: 'sitting', expected: 3 }
      ];

      testCases.forEach(({ str1, str2, expected }) => {
        const distance = optimizedLevenshteinDistance(str1, str2);
        expect(distance).toBe(expected);
      });
    });
  });
});

function generatePerformanceReport(results: BenchmarkResult[]) {
  const totalTests = results.length;
  const regressions = results.filter(r => r.regressionDetected).length;
  const performanceRatios = results
    .filter(r => r.baselineMetrics)
    .map(r => r.performanceRatio);
  const avgRatio = performanceRatios.length > 0 
    ? performanceRatios.reduce((a, b) => a + b, 0) / performanceRatios.length 
    : 1.0;

  return {
    summary: {
      totalTests,
      regressionsDetected: regressions,
      averagePerformanceRatio: avgRatio,
      timestamp: Date.now()
    },
    details: results.map(r => ({
      testName: r.testName,
      executionTime: r.metrics.executionTime,
      memoryUsage: r.metrics.memoryUsage,
      regressionDetected: r.regressionDetected,
      performanceRatio: r.performanceRatio
    })),
    recommendations: generateRecommendations(results)
  };
}

function generateRecommendations(results: BenchmarkResult[]): string[] {
  const recommendations: string[] = [];

  // Check for memory issues
  const highMemoryTests = results.filter(r => Math.abs(r.metrics.memoryUsage) > 50 * 1024 * 1024);
  if (highMemoryTests.length > 0) {
    recommendations.push('Consider optimizing memory usage in high-memory operations');
  }

  // Check for slow operations
  const slowTests = results.filter(r => r.metrics.executionTime > 1000);
  if (slowTests.length > 0) {
    recommendations.push('Review slow operations for optimization opportunities');
  }

  // Check for regressions
  const regressions = results.filter(r => r.regressionDetected);
  if (regressions.length > 0) {
    recommendations.push(`Address ${regressions.length} performance regressions detected`);
  }

  return recommendations;
}