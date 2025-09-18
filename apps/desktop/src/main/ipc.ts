import { ipcMain } from 'electron';
import {
  createWorkspace,
  fetchHealth,
  listProjects,
  uploadWorkspaceDocument,
} from './orchestrator-client';

export function registerIpcHandlers(): void {
  ipcMain.handle('orchestrator:health', async () => {
    const health = await fetchHealth();
    return health;
  });

  ipcMain.handle('orchestrator:list-projects', async () => {
    const projects = await listProjects();
    return projects;
  });

  ipcMain.handle('orchestrator:create-workspace', async (_event, projectPath: string) => {
    const project = await createWorkspace(projectPath);
    return project;
  });

  ipcMain.handle(
    'orchestrator:upload-document',
    async (_event, workspaceName: string, relativePath: string, content: string) => {
      const response = await uploadWorkspaceDocument(workspaceName, {
        relative_path: relativePath,
        content,
      });
      return response;
    },
  );
}
