import { contextBridge, ipcRenderer } from 'electron';
import type {
  CreateSpecRequest,
  UpdateDocumentRequest,
  ExecuteTaskRequest,
  UpdateTaskStatusRequest,
  ApprovePhaseRequest,
} from './orchestrator-client';

contextBridge.exposeInMainWorld('ecocode', {
  fetchHealth: () => ipcRenderer.invoke('orchestrator:health'),
  listProjects: () => ipcRenderer.invoke('orchestrator:list-projects'),
  createWorkspace: (projectPath: string) =>
    ipcRenderer.invoke('orchestrator:create-workspace', projectPath),
  uploadDocument: (workspaceName: string, relativePath: string, content: string) =>
    ipcRenderer.invoke('orchestrator:upload-document', workspaceName, relativePath, content),
  
  // Spec Management API
  specs: {
    create: (request: CreateSpecRequest) => ipcRenderer.invoke('specs:create', request),
    list: () => ipcRenderer.invoke('specs:list'),
    get: (specId: string) => ipcRenderer.invoke('specs:get', specId),
    
    // Document Updates
    updateRequirements: (specId: string, request: UpdateDocumentRequest) =>
      ipcRenderer.invoke('specs:update-requirements', specId, request),
    updateDesign: (specId: string, request: UpdateDocumentRequest) =>
      ipcRenderer.invoke('specs:update-design', specId, request),
    updateTasks: (specId: string, request: UpdateDocumentRequest) =>
      ipcRenderer.invoke('specs:update-tasks', specId, request),
    
    // Task Execution
    executeTask: (specId: string, taskId: string, request: ExecuteTaskRequest) =>
      ipcRenderer.invoke('specs:execute-task', specId, taskId, request),
    updateTaskStatus: (specId: string, taskId: string, request: UpdateTaskStatusRequest) =>
      ipcRenderer.invoke('specs:update-task-status', specId, taskId, request),
    getProgress: (specId: string) => ipcRenderer.invoke('specs:get-progress', specId),
    
    // Approval Workflow
    approvePhase: (specId: string, phase: string, request: ApprovePhaseRequest) =>
      ipcRenderer.invoke('specs:approve-phase', specId, phase, request),
  },
});
