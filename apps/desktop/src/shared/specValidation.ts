import { ValidationResult, ValidationError, ValidationWarning, SpecFileStructure, WorkflowPhase } from './types';

/**
 * Validates the basic directory structure for a spec
 * Requirements: 7.1, 7.2 - Standardized directory structure and file validation
 */
export class SpecDirectoryValidator {
  private static readonly REQUIRED_FILES = ['requirements.md', 'design.md', 'tasks.md'];
  private static readonly METADATA_FILE = '.spec-metadata.json';
  private static readonly SPEC_BASE_PATH = '.kiro/specs';

  /**
   * Validates that a feature name follows kebab-case format and filesystem constraints
   * Requirements: 7.2 - Kebab-case formatting and filesystem validation
   */
  static validateFeatureName(featureName: string): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // Check kebab-case format
    const kebabCaseRegex = /^[a-z0-9]+(-[a-z0-9]+)*$/;
    if (!kebabCaseRegex.test(featureName)) {
      errors.push({
        code: 'INVALID_FEATURE_NAME_FORMAT',
        message: 'Feature name must be in kebab-case format (lowercase letters, numbers, and hyphens only)',
        field: 'featureName',
        severity: 'error'
      });
    }

    // Check length constraints
    if (featureName.length < 3) {
      errors.push({
        code: 'FEATURE_NAME_TOO_SHORT',
        message: 'Feature name must be at least 3 characters long',
        field: 'featureName',
        severity: 'error'
      });
    }

    if (featureName.length > 50) {
      errors.push({
        code: 'FEATURE_NAME_TOO_LONG',
        message: 'Feature name must be 50 characters or less',
        field: 'featureName',
        severity: 'error'
      });
    }

    // Check for reserved names
    const reservedNames = ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'];
    if (reservedNames.includes(featureName.toLowerCase())) {
      errors.push({
        code: 'RESERVED_FEATURE_NAME',
        message: 'Feature name cannot be a reserved system name',
        field: 'featureName',
        severity: 'error'
      });
    }

    // Check for invalid characters for filesystem
    const invalidChars = /[<>:"/\\|?*\u0000-\u001f]/;
    if (invalidChars.test(featureName)) {
      errors.push({
        code: 'INVALID_FILESYSTEM_CHARS',
        message: 'Feature name contains characters not allowed in filesystem paths',
        field: 'featureName',
        severity: 'error'
      });
    }

    // Warnings for best practices
    if (featureName.startsWith('-') || featureName.endsWith('-')) {
      warnings.push({
        code: 'FEATURE_NAME_HYPHEN_EDGES',
        message: 'Feature name should not start or end with hyphens',
        field: 'featureName',
        suggestion: 'Remove leading or trailing hyphens'
      });
    }

    if (featureName.includes('--')) {
      warnings.push({
        code: 'CONSECUTIVE_HYPHENS',
        message: 'Feature name should not contain consecutive hyphens',
        field: 'featureName',
        suggestion: 'Use single hyphens to separate words'
      });
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Generates the expected file structure for a spec
   * Requirements: 7.1 - Standardized directory structure
   */
  static generateSpecFileStructure(featureName: string): SpecFileStructure {
    const basePath = `${this.SPEC_BASE_PATH}/${featureName}`;
    
    return {
      specId: featureName,
      basePath,
      files: {
        requirements: `${basePath}/requirements.md`,
        design: `${basePath}/design.md`,
        tasks: `${basePath}/tasks.md`,
        metadata: `${basePath}/${this.METADATA_FILE}`
      }
    };
  }

  /**
   * Validates the basic structure of a spec directory
   * Requirements: 7.6 - File structure validation with detailed error reporting
   */
  static validateSpecStructure(specFileStructure: SpecFileStructure): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // Validate base path format
    const expectedBasePath = `${this.SPEC_BASE_PATH}/${specFileStructure.specId}`;
    if (specFileStructure.basePath !== expectedBasePath) {
      errors.push({
        code: 'INVALID_BASE_PATH',
        message: `Base path should be ${expectedBasePath}`,
        field: 'basePath',
        severity: 'error'
      });
    }

    // Validate required file paths
    this.REQUIRED_FILES.forEach(fileName => {
      const fileKey = fileName.replace('.md', '') as keyof typeof specFileStructure.files;
      if (fileKey !== 'metadata') {
        const expectedPath = `${specFileStructure.basePath}/${fileName}`;
        const actualPath = specFileStructure.files[fileKey];
        
        if (actualPath !== expectedPath) {
          errors.push({
            code: 'INVALID_FILE_PATH',
            message: `${fileName} path should be ${expectedPath}`,
            field: `files.${String(fileKey)}`,
            severity: 'error'
          });
        }
      }
    });

    // Validate metadata file path
    const expectedMetadataPath = `${specFileStructure.basePath}/${this.METADATA_FILE}`;
    if (specFileStructure.files.metadata !== expectedMetadataPath) {
      errors.push({
        code: 'INVALID_METADATA_PATH',
        message: `Metadata file path should be ${expectedMetadataPath}`,
        field: 'files.metadata',
        severity: 'error'
      });
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Validates workflow phase transitions
   * Requirements: 1.1, 1.2 - Workflow state management and validation
   */
  static validatePhaseTransition(currentPhase: WorkflowPhase, targetPhase: WorkflowPhase): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    const validTransitions: Record<WorkflowPhase, WorkflowPhase[]> = {
      [WorkflowPhase.REQUIREMENTS]: [WorkflowPhase.DESIGN],
      [WorkflowPhase.DESIGN]: [WorkflowPhase.REQUIREMENTS, WorkflowPhase.TASKS],
      [WorkflowPhase.TASKS]: [WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN, WorkflowPhase.EXECUTION],
      [WorkflowPhase.EXECUTION]: [WorkflowPhase.EXECUTION] // Can stay in execution for multiple tasks
    };

    if (!validTransitions[currentPhase]?.includes(targetPhase)) {
      errors.push({
        code: 'INVALID_PHASE_TRANSITION',
        message: `Cannot transition from ${currentPhase} to ${targetPhase}`,
        field: 'targetPhase',
        severity: 'error'
      });
    }

    // Warning for backward transitions
    const phaseOrder = [WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN, WorkflowPhase.TASKS, WorkflowPhase.EXECUTION];
    const currentIndex = phaseOrder.indexOf(currentPhase);
    const targetIndex = phaseOrder.indexOf(targetPhase);

    if (targetIndex < currentIndex && targetPhase !== WorkflowPhase.EXECUTION) {
      warnings.push({
        code: 'BACKWARD_PHASE_TRANSITION',
        message: `Transitioning backward from ${currentPhase} to ${targetPhase}`,
        field: 'targetPhase',
        suggestion: 'Consider if this backward transition is necessary and ensure dependent documents are updated'
      });
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Generates a kebab-case feature name from a rough idea
   * Requirements: 1.1 - Automatic kebab-case feature name generation
   */
  static generateFeatureName(roughIdea: string): string {
    return roughIdea
      .toLowerCase()
      .trim()
      // Replace spaces and underscores with hyphens
      .replace(/[\s_]+/g, '-')
      // Remove non-alphanumeric characters except hyphens
      .replace(/[^a-z0-9-]/g, '')
      // Remove consecutive hyphens
      .replace(/-+/g, '-')
      // Remove leading/trailing hyphens
      .replace(/^-+|-+$/g, '')
      // Limit length
      .substring(0, 50);
  }

  /**
   * Validates that a feature name is unique within existing specs
   * Requirements: 1.2 - Uniqueness checking for feature names
   */
  static async validateFeatureNameUniqueness(
    featureName: string, 
    existingSpecs: string[]
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    if (existingSpecs.includes(featureName)) {
      errors.push({
        code: 'DUPLICATE_FEATURE_NAME',
        message: `A spec with the name '${featureName}' already exists`,
        field: 'featureName',
        severity: 'error'
      });
    }

    // Check for similar names that might cause confusion
    const similarNames = existingSpecs.filter(name => {
      const similarity = this.calculateSimilarity(featureName, name);
      return similarity > 0.8 && similarity < 1.0;
    });

    if (similarNames.length > 0) {
      warnings.push({
        code: 'SIMILAR_FEATURE_NAMES',
        message: `Similar spec names exist: ${similarNames.join(', ')}`,
        field: 'featureName',
        suggestion: 'Consider using a more distinctive name to avoid confusion'
      });
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }

  /**
   * Calculates similarity between two strings using optimized Levenshtein distance
   * Uses the new OptimizedLevenshteinCalculator for better performance
   */
  private static calculateSimilarity(str1: string, str2: string): number {
    return OptimizedLevenshteinCalculator.calculateSimilarity(str1, str2);
  }
}

/**
 * Space-optimized Levenshtein distance calculator
 * Requirements: 6.1, 6.2, 6.3, 6.4 - Performance optimization with O(min(m,n)) space complexity
 */
export class OptimizedLevenshteinCalculator {
  private static readonly DEFAULT_MAX_DISTANCE = 1000;
  private static readonly EARLY_TERMINATION_THRESHOLD = 0.1;

  /**
   * Calculates Levenshtein distance between two strings with space optimization
   * Uses O(min(m,n)) space complexity instead of O(m*n)
   * Requirements: 6.1, 6.2 - Space-optimized algorithm with early termination
   */
  static calculateDistance(str1: string, str2: string, maxDistance?: number): number {
    // Early termination for identical strings
    if (str1 === str2) {
      return 0;
    }

    // Early termination for empty strings
    if (str1.length === 0) return str2.length;
    if (str2.length === 0) return str1.length;

    // Apply maximum distance threshold for performance
    const threshold = maxDistance ?? this.DEFAULT_MAX_DISTANCE;
    const maxLength = Math.max(str1.length, str2.length);
    if (maxLength > threshold) {
      // For very large strings, return early approximation
      return Math.abs(str1.length - str2.length);
    }

    // Ensure str1 is the shorter string for space optimization
    let shortStr = str1;
    let longStr = str2;
    if (str1.length > str2.length) {
      shortStr = str2;
      longStr = str1;
    }

    const shortLen = shortStr.length;
    const longLen = longStr.length;

    // Use only two arrays instead of full matrix - O(min(m,n)) space
    let previousRow = Array(shortLen + 1).fill(0);
    let currentRow = Array(shortLen + 1).fill(0);

    // Initialize first row
    for (let i = 0; i <= shortLen; i++) {
      previousRow[i] = i;
    }

    // Calculate distance row by row
    for (let i = 1; i <= longLen; i++) {
      currentRow[0] = i;

      for (let j = 1; j <= shortLen; j++) {
        const cost = longStr[i - 1] === shortStr[j - 1] ? 0 : 1;
        currentRow[j] = Math.min(
          currentRow[j - 1] + 1,      // insertion
          previousRow[j] + 1,         // deletion
          previousRow[j - 1] + cost   // substitution
        );
      }

      // Early termination if distance is getting too large
      const minInRow = Math.min(...currentRow);
      if (minInRow > threshold * this.EARLY_TERMINATION_THRESHOLD) {
        return threshold;
      }

      // Swap arrays for next iteration
      [previousRow, currentRow] = [currentRow, previousRow];
    }

    return previousRow[shortLen];
  }

  /**
   * Calculates similarity ratio between two strings (0.0 to 1.0)
   * Requirements: 6.3, 6.4 - Optimized similarity calculation with memory efficiency
   */
  static calculateSimilarity(str1: string, str2: string, maxDistance?: number): number {
    // Early termination for identical strings
    if (str1 === str2) {
      return 1.0;
    }

    const distance = this.calculateDistance(str1, str2, maxDistance);
    const maxLength = Math.max(str1.length, str2.length);
    
    // Handle edge case of empty strings
    if (maxLength === 0) {
      return 1.0;
    }

    return (maxLength - distance) / maxLength;
  }

  /**
   * Batch calculates similarities for multiple string pairs
   * Useful for performance when comparing against multiple candidates
   * Requirements: 6.4 - Memory efficiency for batch operations
   */
  static calculateSimilarities(
    target: string, 
    candidates: string[], 
    maxDistance?: number
  ): Array<{ candidate: string; similarity: number; distance: number }> {
    return candidates.map(candidate => {
      const distance = this.calculateDistance(target, candidate, maxDistance);
      const maxLength = Math.max(target.length, candidate.length);
      const similarity = maxLength === 0 ? 1.0 : (maxLength - distance) / maxLength;
      
      return {
        candidate,
        similarity,
        distance
      };
    });
  }

  /**
   * Finds the most similar string from a list of candidates
   * Requirements: 6.1, 6.4 - Performance optimization for similarity matching
   */
  static findMostSimilar(
    target: string, 
    candidates: string[], 
    maxDistance?: number
  ): { candidate: string; similarity: number; distance: number } | null {
    if (candidates.length === 0) {
      return null;
    }

    let bestMatch = {
      candidate: candidates[0],
      similarity: this.calculateSimilarity(target, candidates[0], maxDistance),
      distance: this.calculateDistance(target, candidates[0], maxDistance)
    };

    for (let i = 1; i < candidates.length; i++) {
      const similarity = this.calculateSimilarity(target, candidates[i], maxDistance);
      if (similarity > bestMatch.similarity) {
        bestMatch = {
          candidate: candidates[i],
          similarity,
          distance: this.calculateDistance(target, candidates[i], maxDistance)
        };
      }
    }

    return bestMatch;
  }
}