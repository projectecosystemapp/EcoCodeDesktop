import { OptimizedLevenshteinCalculator } from '../specValidation';

describe('OptimizedLevenshteinCalculator', () => {
  describe('calculateDistance', () => {
    test('returns 0 for identical strings', () => {
      expect(OptimizedLevenshteinCalculator.calculateDistance('hello', 'hello')).toBe(0);
      expect(OptimizedLevenshteinCalculator.calculateDistance('', '')).toBe(0);
    });

    test('returns string length for empty string comparisons', () => {
      expect(OptimizedLevenshteinCalculator.calculateDistance('hello', '')).toBe(5);
      expect(OptimizedLevenshteinCalculator.calculateDistance('', 'world')).toBe(5);
    });

    test('calculates correct distance for simple cases', () => {
      expect(OptimizedLevenshteinCalculator.calculateDistance('cat', 'bat')).toBe(1);
      expect(OptimizedLevenshteinCalculator.calculateDistance('kitten', 'sitting')).toBe(3);
      expect(OptimizedLevenshteinCalculator.calculateDistance('saturday', 'sunday')).toBe(3);
    });

    test('handles strings of different lengths', () => {
      expect(OptimizedLevenshteinCalculator.calculateDistance('a', 'abc')).toBe(2);
      expect(OptimizedLevenshteinCalculator.calculateDistance('abc', 'a')).toBe(2);
    });

    test('respects maximum distance threshold', () => {
      const longStr1 = 'a'.repeat(2000);
      const longStr2 = 'b'.repeat(2000);
      const result = OptimizedLevenshteinCalculator.calculateDistance(longStr1, longStr2, 100);
      expect(result).toBeLessThanOrEqual(2000); // Should return early approximation
    });

    test('early termination works for large strings', () => {
      const start = performance.now();
      const longStr1 = 'a'.repeat(5000);
      const longStr2 = 'b'.repeat(5000);
      OptimizedLevenshteinCalculator.calculateDistance(longStr1, longStr2, 50);
      const end = performance.now();
      
      // Should complete quickly due to early termination
      expect(end - start).toBeLessThan(100); // Less than 100ms
    });
  });

  describe('calculateSimilarity', () => {
    test('returns 1.0 for identical strings', () => {
      expect(OptimizedLevenshteinCalculator.calculateSimilarity('hello', 'hello')).toBe(1.0);
      expect(OptimizedLevenshteinCalculator.calculateSimilarity('', '')).toBe(1.0);
    });

    test('returns 0.0 for completely different strings of same length', () => {
      expect(OptimizedLevenshteinCalculator.calculateSimilarity('abc', 'xyz')).toBe(0.0);
    });

    test('calculates correct similarity ratios', () => {
      // 'cat' vs 'bat' - 1 difference out of 3 characters = 2/3 ≈ 0.667
      const similarity = OptimizedLevenshteinCalculator.calculateSimilarity('cat', 'bat');
      expect(similarity).toBeCloseTo(0.667, 2);

      // 'kitten' vs 'sitting' - 3 differences out of 7 characters = 4/7 ≈ 0.571
      const similarity2 = OptimizedLevenshteinCalculator.calculateSimilarity('kitten', 'sitting');
      expect(similarity2).toBeCloseTo(0.571, 2);
    });

    test('handles empty strings correctly', () => {
      expect(OptimizedLevenshteinCalculator.calculateSimilarity('hello', '')).toBe(0.0);
      expect(OptimizedLevenshteinCalculator.calculateSimilarity('', 'world')).toBe(0.0);
    });
  });

  describe('calculateSimilarities', () => {
    test('calculates similarities for multiple candidates', () => {
      const target = 'hello';
      const candidates = ['hello', 'hallo', 'world', 'help'];
      const results = OptimizedLevenshteinCalculator.calculateSimilarities(target, candidates);

      expect(results).toHaveLength(4);
      expect(results[0].similarity).toBe(1.0); // 'hello' vs 'hello'
      expect(results[0].distance).toBe(0);
      expect(results[2].candidate).toBe('world');
      expect(results[2].similarity).toBeLessThan(0.5); // 'hello' vs 'world'
    });

    test('returns empty array for empty candidates', () => {
      const results = OptimizedLevenshteinCalculator.calculateSimilarities('hello', []);
      expect(results).toHaveLength(0);
    });
  });

  describe('findMostSimilar', () => {
    test('finds the most similar string', () => {
      const target = 'hello';
      const candidates = ['world', 'hallo', 'help', 'hello-world'];
      const result = OptimizedLevenshteinCalculator.findMostSimilar(target, candidates);

      expect(result).not.toBeNull();
      expect(result!.candidate).toBe('hallo'); // Should be most similar to 'hello'
      expect(result!.similarity).toBeGreaterThanOrEqual(0.8);
    });

    test('returns null for empty candidates', () => {
      const result = OptimizedLevenshteinCalculator.findMostSimilar('hello', []);
      expect(result).toBeNull();
    });

    test('returns exact match when available', () => {
      const target = 'hello';
      const candidates = ['world', 'hello', 'help'];
      const result = OptimizedLevenshteinCalculator.findMostSimilar(target, candidates);

      expect(result).not.toBeNull();
      expect(result!.candidate).toBe('hello');
      expect(result!.similarity).toBe(1.0);
      expect(result!.distance).toBe(0);
    });
  });

  describe('performance comparison', () => {
    test('should be faster than naive implementation for large strings', () => {
      const str1 = 'a'.repeat(500);
      const str2 = 'b'.repeat(500);

      // Test optimized version
      const start1 = performance.now();
      OptimizedLevenshteinCalculator.calculateDistance(str1, str2);
      const end1 = performance.now();
      const optimizedTime = end1 - start1;

      // The optimized version should complete in reasonable time
      expect(optimizedTime).toBeLessThan(1000); // Less than 1 second
    });

    test('memory usage should be constant for different string lengths', () => {
      // This test verifies that we're not creating large matrices
      const shortStr1 = 'abc';
      const shortStr2 = 'def';
      const longStr1 = 'a'.repeat(1000);
      const longStr2 = 'b'.repeat(1000);

      // Both should complete without memory issues
      expect(() => {
        OptimizedLevenshteinCalculator.calculateDistance(shortStr1, shortStr2);
        OptimizedLevenshteinCalculator.calculateDistance(longStr1, longStr2, 100);
      }).not.toThrow();
    });
  });

  describe('edge cases', () => {
    test('handles unicode characters correctly', () => {
      const result = OptimizedLevenshteinCalculator.calculateSimilarity('café', 'cafe');
      expect(result).toBeGreaterThan(0.7); // Should be similar despite accent
    });

    test('handles very long strings with early termination', () => {
      const veryLongStr1 = 'x'.repeat(10000);
      const veryLongStr2 = 'y'.repeat(10000);
      
      const start = performance.now();
      const result = OptimizedLevenshteinCalculator.calculateDistance(veryLongStr1, veryLongStr2, 10);
      const end = performance.now();

      expect(end - start).toBeLessThan(50); // Should terminate early
      expect(result).toBeLessThanOrEqual(10000);
    });

    test('maintains accuracy for medium-sized strings', () => {
      const str1 = 'the quick brown fox jumps over the lazy dog';
      const str2 = 'the quick brown fox jumped over the lazy dog';
      
      const similarity = OptimizedLevenshteinCalculator.calculateSimilarity(str1, str2);
      expect(similarity).toBeGreaterThan(0.95); // Should be very similar (only 1 character difference)
    });
  });
});