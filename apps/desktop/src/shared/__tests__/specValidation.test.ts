import { SpecDirectoryValidator, OptimizedLevenshteinCalculator } from '../specValidation';

/**
 * Tests for SpecDirectoryValidator to ensure backward compatibility
 * Requirements: 6.2 - Ensure backward compatibility with existing validation logic
 */
describe('SpecDirectoryValidator', () => {
  describe('validateFeatureNameUniqueness', () => {
    test('detects similar names using optimized algorithm', async () => {
      const existingSpecs = [
        'user-authentication',
        'data-validation',
        'api-integration'
      ];

      // Test with a name that should be above the 0.8 similarity threshold
      const result = await SpecDirectoryValidator.validateFeatureNameUniqueness(
        'user-authentications', // Very similar to 'user-authentication' (just adds 's')
        existingSpecs
      );

      expect(result.isValid).toBe(true); // Should be valid (not duplicate)
      expect(result.errors).toHaveLength(0);
      expect(result.warnings).toHaveLength(1); // Should warn about similarity
      expect(result.warnings[0].code).toBe('SIMILAR_FEATURE_NAMES');
      expect(result.warnings[0].message).toContain('user-authentication');
    });

    test('detects exact duplicates', async () => {
      const existingSpecs = [
        'user-authentication',
        'data-validation'
      ];

      const result = await SpecDirectoryValidator.validateFeatureNameUniqueness(
        'user-authentication', // Exact duplicate
        existingSpecs
      );

      expect(result.isValid).toBe(false);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].code).toBe('DUPLICATE_FEATURE_NAME');
    });

    test('handles empty existing specs list', async () => {
      const result = await SpecDirectoryValidator.validateFeatureNameUniqueness(
        'new-feature',
        []
      );

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
      expect(result.warnings).toHaveLength(0);
    });

    test('similarity detection works with various name patterns', async () => {
      const existingSpecs = [
        'security-fixes',
        'performance-optimization',
        'ui-improvements'
      ];

      // Test with a name that should be above the similarity threshold
      const result1 = await SpecDirectoryValidator.validateFeatureNameUniqueness(
        'security-fix', // Very similar to 'security-fixes'
        existingSpecs
      );

      expect(result1.isValid).toBe(true);
      expect(result1.warnings).toHaveLength(1);
      expect(result1.warnings[0].code).toBe('SIMILAR_FEATURE_NAMES');

      // Test dissimilar name
      const result2 = await SpecDirectoryValidator.validateFeatureNameUniqueness(
        'completely-different-name',
        existingSpecs
      );

      expect(result2.isValid).toBe(true);
      expect(result2.warnings).toHaveLength(0);
    });

    test('performance is acceptable for large spec lists', async () => {
      // Create a large list of existing specs
      const existingSpecs = Array.from({ length: 1000 }, (_, i) => `spec-${i}`);

      const start = performance.now();
      const result = await SpecDirectoryValidator.validateFeatureNameUniqueness(
        'new-spec-name',
        existingSpecs
      );
      const end = performance.now();

      expect(result.isValid).toBe(true);
      expect(end - start).toBeLessThan(100); // Should complete within 100ms
    });
  });

  describe('generateFeatureName', () => {
    test('generates valid kebab-case names', () => {
      const testCases = [
        ['User Authentication System', 'user-authentication-system'],
        ['API Integration', 'api-integration'],
        ['Data_Validation_Module', 'data-validation-module'],
        ['Security & Performance Fixes', 'security-performance-fixes'],
        ['  Multiple   Spaces  ', 'multiple-spaces'],
        ['Special!@#$%Characters', 'specialcharacters']
      ];

      testCases.forEach(([input, expected]) => {
        const result = SpecDirectoryValidator.generateFeatureName(input);
        expect(result).toBe(expected);
      });
    });

    test('handles edge cases', () => {
      expect(SpecDirectoryValidator.generateFeatureName('')).toBe('');
      expect(SpecDirectoryValidator.generateFeatureName('   ')).toBe('');
      expect(SpecDirectoryValidator.generateFeatureName('a'.repeat(100))).toHaveLength(50);
    });
  });

  describe('validateFeatureName', () => {
    test('validates kebab-case format', () => {
      const validNames = [
        'user-authentication',
        'api-integration',
        'data-validation',
        'simple',
        'multi-word-feature-name'
      ];

      validNames.forEach(name => {
        const result = SpecDirectoryValidator.validateFeatureName(name);
        expect(result.isValid).toBe(true);
      });
    });

    test('rejects invalid formats', () => {
      const invalidNames = [
        'UserAuthentication', // PascalCase
        'user_authentication', // snake_case
        'user authentication', // spaces
        'user--authentication', // double hyphens
        '-user-authentication', // leading hyphen
        'user-authentication-', // trailing hyphen
        'ab', // too short
        'a'.repeat(51), // too long
        'user@authentication', // invalid characters
      ];

      invalidNames.forEach(name => {
        const result = SpecDirectoryValidator.validateFeatureName(name);
        expect(result.isValid).toBe(false);
      });
    });
  });

  describe('validateSpecStructure', () => {
    test('validates correct structure', () => {
      const structure = SpecDirectoryValidator.generateSpecFileStructure('test-feature');
      const result = SpecDirectoryValidator.validateSpecStructure(structure);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    test('detects invalid structure', () => {
      const invalidStructure = {
        specId: 'test-feature',
        basePath: '.kiro/specs/wrong-path',
        files: {
          requirements: '.kiro/specs/test-feature/requirements.md',
          design: '.kiro/specs/test-feature/design.md',
          tasks: '.kiro/specs/test-feature/tasks.md',
          metadata: '.kiro/specs/test-feature/.spec-metadata.json'
        }
      };

      const result = SpecDirectoryValidator.validateSpecStructure(invalidStructure);
      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(0);
    });
  });
});