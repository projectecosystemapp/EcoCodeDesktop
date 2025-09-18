import type {
  HealthResponse,
  ProjectInfo,
  WorkspaceDocumentResponse,
} from '../shared/types';

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
    };
  }
}

export {};
