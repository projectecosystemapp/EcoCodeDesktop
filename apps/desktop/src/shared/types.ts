export interface ProjectInfo {
  name: string;
  path: string;
  has_workspace: boolean;
  workspace_path?: string | null;
}

export interface ProjectListResponse {
  projects: ProjectInfo[];
}

export interface WorkspaceDocumentPayload {
  relative_path: string;
  content: string;
}

export interface WorkspaceDocumentResponse {
  stored_path: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

// Spec-Driven Workflow Types

export enum WorkflowPhase {
  REQUIREMENTS = 'requirements',
  DESIGN = 'design',
  TASKS = 'tasks',
  EXECUTION = 'execution'
}

export enum WorkflowStatus {
  DRAFT = 'draft',
  IN_REVIEW = 'in_review',
  APPROVED = 'approved',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  ERROR = 'error'
}

export enum TaskStatus {
  NOT_STARTED = 'not_started',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  BLOCKED = 'blocked'
}

export enum DocumentType {
  REQUIREMENTS = 'requirements',
  DESIGN = 'design',
  TASKS = 'tasks'
}

export interface DocumentMetadata {
  createdAt: Date;
  updatedAt: Date;
  version: string;
  checksum: string;
}

export interface ApprovalRecord {
  approved: boolean;
  approvedAt: Date;
  feedback?: string;
  iteration: number;
}

export interface UserStory {
  role: string;
  feature: string;
  benefit: string;
}

export interface AcceptanceCriterion {
  id: string;
  condition: string;
  action: string;
  result: string;
  format: 'WHEN_THEN' | 'IF_THEN' | 'GIVEN_WHEN_THEN';
}

export interface Requirement {
  id: string;
  userStory: UserStory;
  acceptanceCriteria: AcceptanceCriterion[];
}

export interface RequirementsDocument {
  introduction: string;
  requirements: Requirement[];
  metadata: DocumentMetadata;
}

export interface ArchitectureSection {
  systemBoundaries: string;
  dataFlow: string;
  integrationPoints: string;
  technologyStack: string;
}

export interface ComponentSection {
  components: string;
  interfaces: string;
  interactions: string;
}

export interface DataModelSection {
  schemas: string;
  relationships: string;
  validation: string;
  persistence: string;
}

export interface ErrorHandlingSection {
  errorScenarios: string;
  recoveryStrategies: string;
  logging: string;
  userExperience: string;
}

export interface TestingStrategySection {
  unitTesting: string;
  integrationTesting: string;
  endToEndTesting: string;
  coverage: string;
}

export interface DesignDocument {
  overview: string;
  architecture: ArchitectureSection;
  components: ComponentSection;
  dataModels: DataModelSection;
  errorHandling: ErrorHandlingSection;
  testingStrategy: TestingStrategySection;
  metadata: DocumentMetadata;
}

export interface Task {
  id: string;
  description: string;
  requirements: string[];
  dependencies: string[];
  estimatedEffort: number;
  status: TaskStatus;
  subtasks: Task[];
}

export interface TasksDocument {
  tasks: Task[];
  metadata: DocumentMetadata;
  progress: {
    total: number;
    completed: number;
    inProgress: number;
    notStarted: number;
  };
}

export interface SpecDocuments {
  requirements?: RequirementsDocument;
  design?: DesignDocument;
  tasks?: TasksDocument;
}

export interface SpecificationWorkflow {
  id: string;
  featureName: string;
  description: string;
  currentPhase: WorkflowPhase;
  status: WorkflowStatus;
  documents: SpecDocuments;
  metadata: {
    createdAt: Date;
    updatedAt: Date;
    createdBy: string;
    version: string;
  };
  approvals: {
    requirements?: ApprovalRecord;
    design?: ApprovalRecord;
    tasks?: ApprovalRecord;
  };
}

export interface SpecFileStructure {
  specId: string;
  basePath: string;
  files: {
    requirements: string; // requirements.md
    design: string;       // design.md
    tasks: string;        // tasks.md
    metadata: string;     // .spec-metadata.json
  };
}

export interface SpecMetadata {
  id: string;
  featureName: string;
  version: string;
  createdAt: string;
  updatedAt: string;
  currentPhase: WorkflowPhase;
  status: WorkflowStatus;
  checksum: {
    requirements?: string;
    design?: string;
    tasks?: string;
  };
}

export interface SpecSummary {
  id: string;
  featureName: string;
  currentPhase: WorkflowPhase;
  status: WorkflowStatus;
  lastUpdated: Date;
  progress: number;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
}

export interface ValidationError {
  code: string;
  message: string;
  field?: string;
  severity: 'error' | 'warning';
}

export interface ValidationWarning {
  code: string;
  message: string;
  field?: string;
  suggestion?: string;
}

// Security Types

export interface SecurityEvent {
  eventType: 'url_blocked';
  timestamp: Date;
  attemptedUrl: string;
  reason: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface URLValidationResult {
  isValid: boolean;
  reason?: string;
  securityEvent?: SecurityEvent;
}

export interface SecureURLResponse {
  success: boolean;
}
