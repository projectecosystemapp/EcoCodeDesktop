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
