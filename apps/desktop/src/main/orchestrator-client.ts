import axios from 'axios';
import type {
  HealthResponse,
  ProjectInfo,
  ProjectListResponse,
  WorkspaceDocumentPayload,
  WorkspaceDocumentResponse,
} from '../shared/types';

const orchestratorBaseUrl = process.env.ECOCODE_ORCHESTRATOR_URL ?? 'http://127.0.0.1:8890';

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await axios.get<HealthResponse>(`${orchestratorBaseUrl}/health`);
  return response.data;
}

export async function listProjects(): Promise<ProjectInfo[]> {
  const response = await axios.get<ProjectListResponse>(`${orchestratorBaseUrl}/projects`);
  return response.data.projects;
}

export async function createWorkspace(projectPath: string): Promise<ProjectInfo> {
  const response = await axios.post<ProjectInfo>(`${orchestratorBaseUrl}/workspaces`, {
    project_path: projectPath,
  });
  return response.data;
}

export async function uploadWorkspaceDocument(
  workspaceName: string,
  payload: WorkspaceDocumentPayload,
): Promise<WorkspaceDocumentResponse> {
  const response = await axios.post<WorkspaceDocumentResponse>(
    `${orchestratorBaseUrl}/workspaces/${workspaceName}/documents`,
    payload,
  );
  return response.data;
}
