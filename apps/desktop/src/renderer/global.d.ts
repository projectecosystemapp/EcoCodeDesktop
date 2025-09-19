import type {
  HealthResponse,
  ProjectInfo,
  WorkspaceDocumentResponse,
  SpecificationWorkflow,
  SpecSummary,
} from '../shared/types';

import type {
  CreateSpecRequest,
  CreateSpecResponse,
  UpdateDocumentRequest,
  UpdateDocumentResponse,
  ExecuteTaskRequest,
  ExecuteTaskResponse,
  UpdateTaskStatusRequest,
  UpdateTaskStatusResponse,
  ProgressResponse,
  ApprovePhaseRequest,
  ApprovePhaseResponse,
} from '../main/orchestrator-client';

declare global {
  interface Window {
    ecocode: {
      fetchHealth: () => Promise<HealthResponse>;
      listProjects: () => Promise<ProjectInfo[]>;
      createWorkspace: (projectPath: string) => Promise<ProjectInfo>;
      uploadDocument: (
        workspaceName: string,
        relativePath: string,
        content: string,
      ) => Promise<WorkspaceDocumentResponse>;
      
      specs: {
        create: (request: CreateSpecRequest) => Promise<CreateSpecResponse>;
        list: () => Promise<SpecSummary[]>;
        get: (specId: string) => Promise<SpecificationWorkflow>;
        
        updateRequirements: (specId: string, request: UpdateDocumentRequest) => Promise<UpdateDocumentResponse>;
        updateDesign: (specId: string, request: UpdateDocumentRequest) => Promise<UpdateDocumentResponse>;
        updateTasks: (specId: string, request: UpdateDocumentRequest) => Promise<UpdateDocumentResponse>;
        
        executeTask: (specId: string, taskId: string, request: ExecuteTaskRequest) => Promise<ExecuteTaskResponse>;
        updateTaskStatus: (specId: string, taskId: string, request: UpdateTaskStatusRequest) => Promise<UpdateTaskStatusResponse>;
        getProgress: (specId: string) => Promise<ProgressResponse>;
        
        approvePhase: (specId: string, phase: string, request: ApprovePhaseRequest) => Promise<ApprovePhaseResponse>;
      };
    };
  }
}

export {};
