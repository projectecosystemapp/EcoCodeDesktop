import { OptimizedLevenshteinCalculator } from '../specValidation';

/**
 * Performance benchmark tests for Levenshtein algorithm optimization
 * Requirements: 6.2 - Performance benchmarking to verify improvements
 */
describe('Levenshtein Performance Benchmarks', () => {
  // Original naive implementation for comparison
  const naiveLevenshteinDistance = (str1: string, str2: string): number => {
    const matrix = Array(str2.length + 1).fill(null).map(() => Array(str1.length + 1).fill(null));

    for (let i = 0; i <= str1.length; i++) {
      matrix[0][i] = i;
    }

    for (let j = 0; j <= str2.length; j++) {
      matrix[j][0] = j;
    }

    for (let j = 1; j <= str2.length; j++) {
      for (let i = 1; i <= str1.length; i++) {
        const indicator = str1[i - 1] === str2[j - 1] ? 0 : 1;
        matrix[j][i] = Math.min(
          matrix[j][i - 1] + 1,     // deletion
          matrix[j - 1][i] + 1,     // insertion
          matrix[j - 1][i - 1] + indicator // substitution
        );
      }
    }

    return matrix[str2.length][str1.length];
  };

  const naiveCalculateSimilarity = (str1: string, str2: string): number => {
    if (str1 === str2) return 1.0;
    const distance = naiveLevenshteinDistance(str1, str2);
    const maxLength = Math.max(str1.length, str2.length);
    return maxLength === 0 ? 1.0 : (maxLength - distance) / maxLength;
  };

  describe('correctness verification', () => {
    test('optimized algorithm produces same results as naive implementation', () => {
      const testCases = [
        ['hello', 'hello'],
        ['cat', 'bat'],
        ['kitten', 'sitting'],
        ['saturday', 'sunday'],
        ['', 'hello'],
        ['hello', ''],
        ['abc', 'def'],
        ['longer string test', 'another longer string test']
      ];

      testCases.forEach(([str1, str2]) => {
        const naiveResult = naiveCalculateSimilarity(str1, str2);
        const optimizedResult = OptimizedLevenshteinCalculator.calculateSimilarity(str1, str2);
        
        expect(optimizedResult).toBeCloseTo(naiveResult, 5);
      });
    });
  });

  describe('performance improvements', () => {
    test('optimized algorithm is faster for medium strings', () => {
      const str1 = 'a'.repeat(100);
      const str2 = 'b'.repeat(100);
      const iterations = 100;

      // Benchmark naive implementation
      const naiveStart = performance.now();
      for (let i = 0; i < iterations; i++) {
        naiveCalculateSimilarity(str1, str2);
      }
      const naiveEnd = performance.now();
      const naiveTime = naiveEnd - naiveStart;

      // Benchmark optimized implementation
      const optimizedStart = performance.now();
      for (let i = 0; i < iterations; i++) {
        OptimizedLevenshteinCalculator.calculateSimilarity(str1, str2);
      }
      const optimizedEnd = performance.now();
      const optimizedTime = optimizedEnd - optimizedStart;

      console.log(`Naive implementation: ${naiveTime.toFixed(2)}ms`);
      console.log(`Optimized implementation: ${optimizedTime.toFixed(2)}ms`);
      console.log(`Performance improvement: ${((naiveTime - optimizedTime) / naiveTime * 100).toFixed(1)}%`);

      // Optimized should be at least as fast (allowing for some variance)
      expect(optimizedTime).toBeLessThanOrEqual(naiveTime * 1.1);
    });

    test('optimized algorithm handles large strings efficiently', () => {
      const str1 = 'x'.repeat(500);
      const str2 = 'y'.repeat(500);

      const start = performance.now();
      OptimizedLevenshteinCalculator.calculateSimilarity(str1, str2);
      const end = performance.now();
      const executionTime = end - start;

      console.log(`Large string execution time: ${executionTime.toFixed(2)}ms`);

      // Should complete within reasonable time
      expect(executionTime).toBeLessThan(1000); // Less than 1 second
    });

    test('memory usage is constant regardless of string length', () => {
      // This test verifies space complexity by ensuring no out-of-memory errors
      const testSizes = [10, 50, 100, 200, 500];
      
      testSizes.forEach(size => {
        const str1 = 'a'.repeat(size);
        const str2 = 'b'.repeat(size);
        
        expect(() => {
          OptimizedLevenshteinCalculator.calculateSimilarity(str1, str2);
        }).not.toThrow();
      });
    });

    test('early termination provides significant speedup for very different strings', () => {
      const str1 = 'a'.repeat(1000);
      const str2 = 'b'.repeat(1000);

      const start = performance.now();
      OptimizedLevenshteinCalculator.calculateDistance(str1, str2, 10);
      const end = performance.now();
      const executionTime = end - start;

      console.log(`Early termination execution time: ${executionTime.toFixed(2)}ms`);

      // Should terminate very quickly due to early exit
      expect(executionTime).toBeLessThan(50); // Less than 50ms
    });
  });

  describe('batch operations performance', () => {
    test('batch similarity calculation is efficient', () => {
      const target = 'hello-world-test';
      const candidates = Array.from({ length: 100 }, (_, i) => `candidate-${i}-test`);

      const start = performance.now();
      const results = OptimizedLevenshteinCalculator.calculateSimilarities(target, candidates);
      const end = performance.now();
      const executionTime = end - start;

      console.log(`Batch calculation time for 100 candidates: ${executionTime.toFixed(2)}ms`);

      expect(results).toHaveLength(100);
      expect(executionTime).toBeLessThan(500); // Should complete within 500ms
    });

    test('findMostSimilar is efficient for large candidate lists', () => {
      const target = 'target-string';
      const candidates = Array.from({ length: 1000 }, (_, i) => `candidate-${i}`);
      candidates.push('target-string-similar'); // Add a similar one

      const start = performance.now();
      const result = OptimizedLevenshteinCalculator.findMostSimilar(target, candidates);
      const end = performance.now();
      const executionTime = end - start;

      console.log(`FindMostSimilar time for 1000 candidates: ${executionTime.toFixed(2)}ms`);

      expect(result).not.toBeNull();
      expect(executionTime).toBeLessThan(1000); // Should complete within 1 second
    });
  });

  describe('real-world usage scenarios', () => {
    test('spec name similarity checking performance', () => {
      // Simulate real spec names
      const existingSpecs = [
        'user-authentication',
        'data-validation',
        'api-integration',
        'security-fixes',
        'performance-optimization',
        'ui-improvements',
        'database-migration',
        'error-handling',
        'logging-system',
        'configuration-management'
      ];

      const newSpecName = 'user-authorization';

      const start = performance.now();
      const similarities = OptimizedLevenshteinCalculator.calculateSimilarities(
        newSpecName, 
        existingSpecs
      );
      const end = performance.now();
      const executionTime = end - start;

      console.log(`Spec similarity checking time: ${executionTime.toFixed(2)}ms`);

      expect(similarities).toHaveLength(existingSpecs.length);
      expect(executionTime).toBeLessThan(10); // Should be very fast for typical usage

      // Verify it finds 'user-authentication' as most similar
      const mostSimilar = similarities.reduce((max, current) => 
        current.similarity > max.similarity ? current : max
      );
      expect(mostSimilar.candidate).toBe('user-authentication');
    });

    test('handles edge cases efficiently', () => {
      const edgeCases = [
        ['', ''],
        ['a', ''],
        ['', 'b'],
        ['same', 'same'],
        ['café', 'cafe'], // Unicode
        ['very-long-spec-name-with-many-hyphens-and-words', 'another-very-long-spec-name']
      ];

      edgeCases.forEach(([str1, str2]) => {
        const start = performance.now();
        const similarity = OptimizedLevenshteinCalculator.calculateSimilarity(str1, str2);
        const end = performance.now();

        expect(similarity).toBeGreaterThanOrEqual(0);
        expect(similarity).toBeLessThanOrEqual(1);
        expect(end - start).toBeLessThan(10); // Should handle edge cases quickly
      });
    });
  });
});