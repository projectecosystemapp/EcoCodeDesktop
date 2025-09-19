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
import { IPCErrorHandler } from './ipcErrorHandler';
import type {
  CreateSpecRequest,
  UpdateDocumentRequest,
  ExecuteTaskRequest,
  UpdateTaskStatusRequest,
  ApprovePhaseRequest,
} from './orchestrator-client';

export function registerIpcHandlers(): void {
  const fallbacks = IPCErrorHandler.getDefaultFallbacks();

  ipcMain.handle('orchestrator:health', 
    IPCErrorHandler.createSafeIPCHandler(
      async () => {
        return await fetchHealth();
      },
      'orchestrator:health',
      fallbacks.health
    )
  );

  ipcMain.handle('orchestrator:list-projects',
    IPCErrorHandler.createSafeIPCHandler(
      async () => {
        return await listProjects();
      },
      'orchestrator:list-projects',
      fallbacks.projects
    )
  );

  ipcMain.handle('orchestrator:create-workspace',
    IPCErrorHandler.createSafeIPCHandler(
      async (projectPath: string) => {
        return await createWorkspace(projectPath);
      },
      'orchestrator:create-workspace'
    )
  );

  ipcMain.handle('orchestrator:upload-document',
    IPCErrorHandler.createSafeIPCHandler(
      async (workspaceName: string, relativePath: string, content: string) => {
        return await uploadWorkspaceDocument(workspaceName, {
          relative_path: relativePath,
          content,
        });
      },
      'orchestrator:upload-document'
    )
  );

  ipcMain.handle('security:open-url',
    IPCErrorHandler.createSafeIPCHandler(
      async (url: string) => {
        const validationResult = URLValidator.validateURL(url);
        
        if (!validationResult.isValid) {
          throw new Error(`Security violation: ${validationResult.reason}`);
        }

        const { shell } = await import('electron');
        await shell.openExternal(url);
        return { success: true };
      },
      'security:open-url'
    )
  );

  // Spec Management IPC Handlers

  ipcMain.handle('specs:create',
    IPCErrorHandler.createSafeIPCHandler(
      async (request: CreateSpecRequest) => {
        return await createSpec(request);
      },
      'specs:create'
    )
  );

  ipcMain.handle('specs:list',
    IPCErrorHandler.createSafeIPCHandler(
      async () => {
        return await listSpecs();
      },
      'specs:list',
      fallbacks.specs
    )
  );

  ipcMain.handle('specs:get',
    IPCErrorHandler.createSafeIPCHandler(
      async (specId: string) => {
        return await getSpec(specId);
      },
      'specs:get'
    )
  );

  // Document Update IPC Handlers

  ipcMain.handle('specs:update-requirements',
    IPCErrorHandler.createSafeIPCHandler(
      async (specId: string, request: UpdateDocumentRequest) => {
        return await updateRequirements(specId, request);
      },
      'specs:update-requirements'
    )
  );

  ipcMain.handle('specs:update-design',
    IPCErrorHandler.createSafeIPCHandler(
      async (specId: string, request: UpdateDocumentRequest) => {
        return await updateDesign(specId, request);
      },
      'specs:update-design'
    )
  );

  ipcMain.handle('specs:update-tasks',
    IPCErrorHandler.createSafeIPCHandler(
      async (specId: string, request: UpdateDocumentRequest) => {
        return await updateTasks(specId, request);
      },
      'specs:update-tasks'
    )
  );

  // Task Execution IPC Handlers

  ipcMain.handle('specs:execute-task',
    IPCErrorHandler.createSafeIPCHandler(
      async (specId: string, taskId: string, request: ExecuteTaskRequest) => {
        return await executeTask(specId, taskId, request);
      },
      'specs:execute-task'
    )
  );

  ipcMain.handle('specs:update-task-status',
    IPCErrorHandler.createSafeIPCHandler(
      async (specId: string, taskId: string, request: UpdateTaskStatusRequest) => {
        return await updateTaskStatus(specId, taskId, request);
      },
      'specs:update-task-status'
    )
  );

  ipcMain.handle('specs:get-progress',
    IPCErrorHandler.createSafeIPCHandler(
      async (specId: string) => {
        return await getProgress(specId);
      },
      'specs:get-progress',
      fallbacks.progress
    )
  );

  // Approval Workflow IPC Handlers

  ipcMain.handle('specs:approve-phase',
    IPCErrorHandler.createSafeIPCHandler(
      async (specId: string, phase: string, request: ApprovePhaseRequest) => {
        return await approvePhase(specId, phase, request);
      },
      'specs:approve-phase'
    )
  );
}
