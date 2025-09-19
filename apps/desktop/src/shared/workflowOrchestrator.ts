import { 
  SpecificationWorkflow, 
  WorkflowPhase, 
  WorkflowStatus, 
  TaskStatus, 
  ValidationResult,
  ValidationError,
  ValidationWarning,
  SpecSummary,
  Task
} from './types';

/**
 * Core workflow orchestration interfaces and types
 * Requirements: 1.1, 1.2 - Workflow orchestration and state management
 */

export interface WorkflowOrchestrator {
  createSpec(featureIdea: string): Promise<SpecWorkflow>;
  updateSpec(specId: string, phase: WorkflowPhase): Promise<SpecWorkflow>;
  executeTask(specId: string, taskId: string): Promise<TaskResult>;
  getSpecStatus(specId: string): Promise<SpecStatus>;
  listSpecs(): Promise<SpecSummary[]>;
  validateWorkflow(specId: string): Promise<ValidationResult>;
}

export interface SpecWorkflow {
  id: string;
  featureName: string;
  currentPhase: WorkflowPhase;
  documents: WorkflowDocuments;
  status: WorkflowStatus;
  createdAt: Date;
  updatedAt: Date;
}

export interface WorkflowDocuments {
  requirements?: string; // Markdown content
  design?: string;       // Markdown content
  tasks?: string;        // Markdown content
}

export interface SpecStatus {
  id: string;
  featureName: string;
  currentPhase: WorkflowPhase;
  status: WorkflowStatus;
  progress: ProgressMetrics;
  lastActivity: Date;
  approvalStatus: ApprovalStatus;
}

export interface ProgressMetrics {
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  blockedTasks: number;
  overallProgress: number; // 0-100 percentage
}

export interface ApprovalStatus {
  requirements: boolean;
  design: boolean;
  tasks: boolean;
  currentPhaseApproved: boolean;
}

export interface TaskResult {
  taskId: string;
  status: TaskStatus;
  output?: string;
  error?: string;
  filesModified: string[];
  executionTime: number;
}

export interface WorkflowTransition {
  from: WorkflowPhase;
  to: WorkflowPhase;
  requiresApproval: boolean;
  validationRules: ValidationRule[];
}

export interface ValidationRule {
  name: string;
  description: string;
  validate: (workflow: SpecificationWorkflow) => ValidationResult;
}

export interface ExecutionContext {
  specId: string;
  workspacePath: string;
  requirements?: string;
  design?: string;
  projectStructure: ProjectStructure;
  existingCode: CodeContext;
}

export interface ProjectStructure {
  rootPath: string;
  sourceDirectories: string[];
  testDirectories: string[];
  configFiles: string[];
  packageFiles: string[];
}

export interface CodeContext {
  files: CodeFile[];
  dependencies: Dependency[];
  frameworks: string[];
  languages: string[];
}

export interface CodeFile {
  path: string;
  language: string;
  size: number;
  lastModified: Date;
}

export interface Dependency {
  name: string;
  version: string;
  type: 'production' | 'development' | 'peer';
}

/**
 * Workflow state machine implementation
 * Requirements: 1.8, 1.9 - Workflow state transitions and validation
 */
export class WorkflowStateMachine {
  private static readonly WORKFLOW_TRANSITIONS: WorkflowTransition[] = [
    {
      from: WorkflowPhase.REQUIREMENTS,
      to: WorkflowPhase.DESIGN,
      requiresApproval: true,
      validationRules: [
        {
          name: 'requirements_complete',
          description: 'Requirements document must be complete and approved',
          validate: (workflow) => this.validateRequirementsComplete(workflow)
        }
      ]
    },
    {
      from: WorkflowPhase.DESIGN,
      to: WorkflowPhase.TASKS,
      requiresApproval: true,
      validationRules: [
        {
          name: 'design_complete',
          description: 'Design document must be complete and approved',
          validate: (workflow) => this.validateDesignComplete(workflow)
        }
      ]
    },
    {
      from: WorkflowPhase.DESIGN,
      to: WorkflowPhase.REQUIREMENTS,
      requiresApproval: false,
      validationRules: []
    },
    {
      from: WorkflowPhase.TASKS,
      to: WorkflowPhase.EXECUTION,
      requiresApproval: true,
      validationRules: [
        {
          name: 'tasks_complete',
          description: 'Task list must be complete and approved',
          validate: (workflow) => this.validateTasksComplete(workflow)
        }
      ]
    },
    {
      from: WorkflowPhase.TASKS,
      to: WorkflowPhase.DESIGN,
      requiresApproval: false,
      validationRules: []
    },
    {
      from: WorkflowPhase.TASKS,
      to: WorkflowPhase.REQUIREMENTS,
      requiresApproval: false,
      validationRules: []
    },
    {
      from: WorkflowPhase.EXECUTION,
      to: WorkflowPhase.EXECUTION,
      requiresApproval: false,
      validationRules: []
    }
  ];

  static canTransition(from: WorkflowPhase, to: WorkflowPhase): boolean {
    return this.WORKFLOW_TRANSITIONS.some(
      transition => transition.from === from && transition.to === to
    );
  }

  static getTransition(from: WorkflowPhase, to: WorkflowPhase): WorkflowTransition | null {
    return this.WORKFLOW_TRANSITIONS.find(
      transition => transition.from === from && transition.to === to
    ) || null;
  }

  static validateTransition(
    workflow: SpecificationWorkflow, 
    targetPhase: WorkflowPhase
  ): ValidationResult {
    const transition = this.getTransition(workflow.currentPhase, targetPhase);
    
    if (!transition) {
      return {
        isValid: false,
        errors: [{
          code: 'INVALID_TRANSITION',
          message: `Cannot transition from ${workflow.currentPhase} to ${targetPhase}`,
          severity: 'error'
        }],
        warnings: []
      };
    }

    // Run validation rules
    const validationResults = transition.validationRules.map(rule => 
      rule.validate(workflow)
    );

    const allErrors = validationResults.flatMap(result => result.errors);
    const allWarnings = validationResults.flatMap(result => result.warnings);

    return {
      isValid: allErrors.length === 0,
      errors: allErrors,
      warnings: allWarnings
    };
  }

  private static validateRequirementsComplete(workflow: SpecificationWorkflow): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    if (!workflow.documents.requirements) {
      errors.push({
        code: 'MISSING_REQUIREMENTS',
        message: 'Requirements document is missing',
        severity: 'error' as const
      });
    }

    if (!workflow.approvals.requirements?.approved) {
      errors.push({
        code: 'REQUIREMENTS_NOT_APPROVED',
        message: 'Requirements document must be approved before proceeding to design',
        severity: 'error' as const
      });
    }

    return { isValid: errors.length === 0, errors, warnings };
  }

  private static validateDesignComplete(workflow: SpecificationWorkflow): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    if (!workflow.documents.design) {
      errors.push({
        code: 'MISSING_DESIGN',
        message: 'Design document is missing',
        severity: 'error' as const
      });
    }

    if (!workflow.approvals.design?.approved) {
      errors.push({
        code: 'DESIGN_NOT_APPROVED',
        message: 'Design document must be approved before proceeding to tasks',
        severity: 'error' as const
      });
    }

    return { isValid: errors.length === 0, errors, warnings };
  }

  private static validateTasksComplete(workflow: SpecificationWorkflow): ValidationResult {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    if (!workflow.documents.tasks) {
      errors.push({
        code: 'MISSING_TASKS',
        message: 'Tasks document is missing',
        severity: 'error' as const
      });
    }

    if (!workflow.approvals.tasks?.approved) {
      errors.push({
        code: 'TASKS_NOT_APPROVED',
        message: 'Tasks document must be approved before proceeding to execution',
        severity: 'error' as const
      });
    }

    return { isValid: errors.length === 0, errors, warnings };
  }
}

/**
 * Task execution status management
 * Requirements: 4.5, 4.8, 4.9 - Task status tracking and progress management
 */
export class TaskStatusManager {
  static calculateProgress(tasks: Task[]): ProgressMetrics {
    const flatTasks = this.flattenTasks(tasks);
    
    const totalTasks = flatTasks.length;
    const completedTasks = flatTasks.filter(task => task.status === TaskStatus.COMPLETED).length;
    const inProgressTasks = flatTasks.filter(task => task.status === TaskStatus.IN_PROGRESS).length;
    const blockedTasks = flatTasks.filter(task => task.status === TaskStatus.BLOCKED).length;
    
    const overallProgress = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

    return {
      totalTasks,
      completedTasks,
      inProgressTasks,
      blockedTasks,
      overallProgress: Math.round(overallProgress * 100) / 100 // Round to 2 decimal places
    };
  }

  static getNextTask(tasks: Task[]): Task | null {
    const flatTasks = this.flattenTasks(tasks);
    
    // Find first not started task that has no incomplete dependencies
    return flatTasks.find(task => 
      task.status === TaskStatus.NOT_STARTED && 
      this.areTaskDependenciesComplete(task, flatTasks)
    ) || null;
  }

  static updateTaskStatus(tasks: Task[], taskId: string, status: TaskStatus): Task[] {
    return tasks.map(task => {
      if (task.id === taskId) {
        return { ...task, status };
      }
      
      if (task.subtasks.length > 0) {
        const updatedSubtasks = this.updateTaskStatus(task.subtasks, taskId, status);
        
        // If all subtasks are completed, mark parent as completed
        const allSubtasksCompleted = updatedSubtasks.every(subtask => 
          subtask.status === TaskStatus.COMPLETED
        );
        
        return {
          ...task,
          subtasks: updatedSubtasks,
          status: allSubtasksCompleted ? TaskStatus.COMPLETED : task.status
        };
      }
      
      return task;
    });
  }

  private static flattenTasks(tasks: Task[]): Task[] {
    const result: Task[] = [];
    
    for (const task of tasks) {
      result.push(task);
      if (task.subtasks.length > 0) {
        result.push(...this.flattenTasks(task.subtasks));
      }
    }
    
    return result;
  }

  private static areTaskDependenciesComplete(task: Task, allTasks: Task[]): boolean {
    return task.dependencies.every((depId: string) => {
      const dependency = allTasks.find(t => t.id === depId);
      return dependency?.status === TaskStatus.COMPLETED;
    });
  }
}