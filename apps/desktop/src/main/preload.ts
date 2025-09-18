import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('ecocode', {
  fetchHealth: () => ipcRenderer.invoke('orchestrator:health'),
  listProjects: () => ipcRenderer.invoke('orchestrator:list-projects'),
  createWorkspace: (projectPath: string) =>
    ipcRenderer.invoke('orchestrator:create-workspace', projectPath),
  uploadDocument: (workspaceName: string, relativePath: string, content: string) =>
    ipcRenderer.invoke('orchestrator:upload-document', workspaceName, relativePath, content),
});
