import axios from 'axios';
import { ErrorHandler } from '../shared/errorHandler';
import type {
  HealthResponse,
  ProjectInfo,
  ProjectListResponse,
  WorkspaceDocumentPayload,
  WorkspaceDocumentResponse,
  SpecificationWorkflow,
  SpecSummary,
  ValidationResult,
  WorkflowPhase,
  TaskStatus,
} from '../shared/types';

const orchestratorBaseUrl = process.env.ECOCODE_ORCHESTRATOR_URL ?? 'http://127.0.0.1:8890';

export async function fetchHealth(): Promise<HealthResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.get<HealthResponse>(`${orchestratorBaseUrl}/health`);
      return response.data;
    },
    'fetchHealth',
    { maxRetries: 2, baseDelay: 500 }
  );
}

export async function listProjects(): Promise<ProjectInfo[]> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.get<ProjectListResponse>(`${orchestratorBaseUrl}/projects`);
      return response.data.projects;
    },
    'listProjects'
  );
}

export async function createWorkspace(projectPath: string): Promise<ProjectInfo> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.post<ProjectInfo>(`${orchestratorBaseUrl}/workspaces`, {
        project_path: projectPath,
      });
      return response.data;
    },
    'createWorkspace'
  );
}

export async function uploadWorkspaceDocument(
  workspaceName: string,
  payload: WorkspaceDocumentPayload,
): Promise<WorkspaceDocumentResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.post<WorkspaceDocumentResponse>(
        `${orchestratorBaseUrl}/workspaces/${workspaceName}/documents`,
        payload,
      );
      return response.data;
    },
    'uploadWorkspaceDocument'
  );
}

// Spec Management API Functions

export interface CreateSpecRequest {
  feature_idea: string;
  feature_name?: string;
}

export interface CreateSpecResponse {
  id: string;
  feature_name: string;
  current_phase: string;
  status: string;
  created_at: string;
  updated_at: string;
  progress: number;
}

export interface SpecListResponse {
  specs: CreateSpecResponse[];
  total_count: number;
}

export interface SpecDetailResponse {
  id: string;
  feature_name: string;
  current_phase: string;
  status: string;
  created_at: string;
  updated_at: string;
  progress: number;
  documents: {
    requirements?: string;
    design?: string;
    tasks?: string;
  };
  approvals: {
    requirements?: string;
    design?: string;
    tasks?: string;
  };
  metadata: Record<string, any>;
}

export interface UpdateDocumentRequest {
  content: string;
  approve?: boolean;
  feedback?: string;
}

export interface UpdateDocumentResponse {
  success: boolean;
  message: string;
  updated_at: string;
  checksum: string;
}

export interface ExecuteTaskRequest {
  task_description?: string;
}

export interface ExecuteTaskResponse {
  success: boolean;
  message: string;
  task_id: string;
  status: string;
  execution_log: string[];
}

export interface UpdateTaskStatusRequest {
  status: string;
}

export interface UpdateTaskStatusResponse {
  success: boolean;
  message: string;
  task_id: string;
  status: string;
  updated_at: string;
}

export interface ProgressResponse {
  spec_id: string;
  total_tasks: number;
  completed_tasks: number;
  in_progress_tasks: number;
  not_started_tasks: number;
  blocked_tasks: number;
  progress_percentage: number;
  current_phase: string;
  status: string;
}

export interface ApprovePhaseRequest {
  approved: boolean;
  feedback?: string;
}

export interface ApprovePhaseResponse {
  success: boolean;
  message: string;
  phase: string;
  approved: boolean;
  next_phase?: string;
}

export async function createSpec(request: CreateSpecRequest): Promise<CreateSpecResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.post<CreateSpecResponse>(`${orchestratorBaseUrl}/specs`, request);
      return response.data;
    },
    'createSpec'
  );
}

export async function listSpecs(): Promise<SpecSummary[]> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.get<SpecListResponse>(`${orchestratorBaseUrl}/specs`);
      return response.data.specs.map(spec => ({
        id: spec.id,
        featureName: spec.feature_name,
        currentPhase: spec.current_phase as WorkflowPhase,
        status: spec.status as any,
        lastUpdated: new Date(spec.updated_at),
        progress: spec.progress,
      }));
    },
    'listSpecs'
  );
}

export async function getSpec(specId: string): Promise<SpecificationWorkflow> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.get<SpecDetailResponse>(`${orchestratorBaseUrl}/specs/${specId}`);
      const spec = response.data;
      
      return {
        id: spec.id,
        featureName: spec.feature_name,
        description: '', // Not provided by API
        currentPhase: spec.current_phase as WorkflowPhase,
        status: spec.status as unknown,
        documents: {
          requirements: spec.documents.requirements ? {
            introduction: '',
            requirements: [],
            metadata: {
              createdAt: new Date(spec.created_at),
              updatedAt: new Date(spec.updated_at),
              version: '1.0.0',
              checksum: '',
            },
          } : undefined,
          design: spec.documents.design ? {
            overview: '',
            architecture: { systemBoundaries: '', dataFlow: '', integrationPoints: '', technologyStack: '' },
            components: { components: '', interfaces: '', interactions: '' },
            dataModels: { schemas: '', relationships: '', validation: '', persistence: '' },
            errorHandling: { errorScenarios: '', recoveryStrategies: '', logging: '', userExperience: '' },
            testingStrategy: { unitTesting: '', integrationTesting: '', endToEndTesting: '', coverage: '' },
            metadata: {
              createdAt: new Date(spec.created_at),
              updatedAt: new Date(spec.updated_at),
              version: '1.0.0',
              checksum: '',
            },
          } : undefined,
          tasks: spec.documents.tasks ? {
            tasks: [],
            metadata: {
              createdAt: new Date(spec.created_at),
              updatedAt: new Date(spec.updated_at),
              version: '1.0.0',
              checksum: '',
            },
            progress: { total: 0, completed: 0, inProgress: 0, notStarted: 0 },
          } : undefined,
        },
        metadata: {
          createdAt: new Date(spec.created_at),
          updatedAt: new Date(spec.updated_at),
          createdBy: 'user',
          version: '1.0.0',
        },
        approvals: {
          requirements: spec.approvals.requirements ? {
            approved: spec.approvals.requirements === 'approved',
            approvedAt: new Date(spec.updated_at),
            iteration: 1,
          } : undefined,
          design: spec.approvals.design ? {
            approved: spec.approvals.design === 'approved',
            approvedAt: new Date(spec.updated_at),
            iteration: 1,
          } : undefined,
          tasks: spec.approvals.tasks ? {
            approved: spec.approvals.tasks === 'approved',
            approvedAt: new Date(spec.updated_at),
            iteration: 1,
          } : undefined,
        },
      };
    },
    'getSpec'
  );
}

export async function updateRequirements(
  specId: string,
  request: UpdateDocumentRequest,
): Promise<UpdateDocumentResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.put<UpdateDocumentResponse>(
        `${orchestratorBaseUrl}/specs/${specId}/requirements`,
        request,
      );
      return response.data;
    },
    'updateRequirements'
  );
}

export async function updateDesign(
  specId: string,
  request: UpdateDocumentRequest,
): Promise<UpdateDocumentResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.put<UpdateDocumentResponse>(
        `${orchestratorBaseUrl}/specs/${specId}/design`,
        request,
      );
      return response.data;
    },
    'updateDesign'
  );
}

export async function updateTasks(
  specId: string,
  request: UpdateDocumentRequest,
): Promise<UpdateDocumentResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.put<UpdateDocumentResponse>(
        `${orchestratorBaseUrl}/specs/${specId}/tasks`,
        request,
      );
      return response.data;
    },
    'updateTasks'
  );
}

export async function executeTask(
  specId: string,
  taskId: string,
  request: ExecuteTaskRequest,
): Promise<ExecuteTaskResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.post<ExecuteTaskResponse>(
        `${orchestratorBaseUrl}/specs/${specId}/tasks/${taskId}/execute`,
        request,
      );
      return response.data;
    },
    'executeTask',
    { maxRetries: 1 } // Task execution should not be retried automatically
  );
}

export async function updateTaskStatus(
  specId: string,
  taskId: string,
  request: UpdateTaskStatusRequest,
): Promise<UpdateTaskStatusResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.put<UpdateTaskStatusResponse>(
        `${orchestratorBaseUrl}/specs/${specId}/tasks/${taskId}/status`,
        request,
      );
      return response.data;
    },
    'updateTaskStatus'
  );
}

export async function getProgress(specId: string): Promise<ProgressResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.get<ProgressResponse>(`${orchestratorBaseUrl}/specs/${specId}/progress`);
      return response.data;
    },
    'getProgress'
  );
}

export async function approvePhase(
  specId: string,
  phase: string,
  request: ApprovePhaseRequest,
): Promise<ApprovePhaseResponse> {
  return ErrorHandler.executeWithRetry(
    async () => {
      const response = await axios.post<ApprovePhaseResponse>(
        `${orchestratorBaseUrl}/specs/${specId}/approve/${phase}`,
        request,
      );
      return response.data;
    },
    'approvePhase'
  );
}
