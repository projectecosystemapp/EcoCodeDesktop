import { ipcMain } from 'electron';
import {
  createWorkspace,
  fetchHealth,
  listProjects,
  uploadWorkspaceDocument,
  createSpec,
  listSpecs,
  getSpec,
  updateRequirements,
  updateDesign,
  updateTasks,
  executeTask,
  updateTaskStatus,
  getProgress,
  approvePhase,
} from './orchestrator-client';
import { URLValidator } from './url-validator';
import type {
  CreateSpecRequest,
  UpdateDocumentRequest,
  ExecuteTaskRequest,
  UpdateTaskStatusRequest,
  ApprovePhaseRequest,
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

  ipcMain.handle('security:open-url', async (_event, url: string) => {
    const validationResult = URLValidator.validateURL(url);
    
    if (!validationResult.isValid) {
      throw new Error(`Security violation: ${validationResult.reason}`);
    }

    const { shell } = await import('electron');
    await shell.openExternal(url);
    return { success: true };
  });

  // Spec Management IPC Handlers

  ipcMain.handle('specs:create', async (_event, request: CreateSpecRequest) => {
    try {
      const spec = await createSpec(request);
      return spec;
    } catch (error) {
      throw new Error(`Failed to create spec: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });

  ipcMain.handle('specs:list', async () => {
    try {
      const specs = await listSpecs();
      return specs;
    } catch (error) {
      throw new Error(`Failed to list specs: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });

  ipcMain.handle('specs:get', async (_event, specId: string) => {
    try {
      const spec = await getSpec(specId);
      return spec;
    } catch (error) {
      throw new Error(`Failed to get spec: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });

  // Document Update IPC Handlers

  ipcMain.handle('specs:update-requirements', async (_event, specId: string, request: UpdateDocumentRequest) => {
    try {
      const result = await updateRequirements(specId, request);
      return result;
    } catch (error) {
      throw new Error(`Failed to update requirements: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });

  ipcMain.handle('specs:update-design', async (_event, specId: string, request: UpdateDocumentRequest) => {
    try {
      const result = await updateDesign(specId, request);
      return result;
    } catch (error) {
      throw new Error(`Failed to update design: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });

  ipcMain.handle('specs:update-tasks', async (_event, specId: string, request: UpdateDocumentRequest) => {
    try {
      const result = await updateTasks(specId, request);
      return result;
    } catch (error) {
      throw new Error(`Failed to update tasks: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });

  // Task Execution IPC Handlers

  ipcMain.handle('specs:execute-task', async (_event, specId: string, taskId: string, request: ExecuteTaskRequest) => {
    try {
      const result = await executeTask(specId, taskId, request);
      return result;
    } catch (error) {
      throw new Error(`Failed to execute task: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });

  ipcMain.handle('specs:update-task-status', async (_event, specId: string, taskId: string, request: UpdateTaskStatusRequest) => {
    try {
      const result = await updateTaskStatus(specId, taskId, request);
      return result;
    } catch (error) {
      throw new Error(`Failed to update task status: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });

  ipcMain.handle('specs:get-progress', async (_event, specId: string) => {
    try {
      const progress = await getProgress(specId);
      return progress;
    } catch (error) {
      throw new Error(`Failed to get progress: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });

  // Approval Workflow IPC Handlers

  ipcMain.handle('specs:approve-phase', async (_event, specId: string, phase: string, request: ApprovePhaseRequest) => {
    try {
      const result = await approvePhase(specId, phase, request);
      return result;
    } catch (error) {
      throw new Error(`Failed to approve phase: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  });
}
