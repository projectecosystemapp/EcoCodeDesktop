import { create } from 'zustand';
import { StoreOperationManager, LoadingState, ErrorState } from '../shared/storeUtils';
import type { HealthResponse, ProjectInfo } from '../shared/types';

type AppState = {
  projects: ProjectInfo[];
  health: HealthResponse | null;
  loading: LoadingState;
  error: ErrorState;
  refreshProjects: () => Promise<void>;
  ensureWorkspace: (projectPath: string) => Promise<void>;
  hydrateHealth: () => Promise<void>;
  clearError: () => void;
  retryLastOperation: () => Promise<void>;
  cleanup: () => void;
};

export const useAppStore = create<AppState>((set, get) => ({
  projects: [],
  health: null,
  loading: StoreOperationManager.createIdleState(),
  error: StoreOperationManager.createSuccessState(),
  
  async refreshProjects() {
    await StoreOperationManager.executeWithTimeout(
      async () => {
        const projects = await (window as any).ecocode.listProjects();
        set({ projects });
      },
      {
        operation: 'refreshProjects',
        timeout: 15000,
        onSuccess: () => {
          console.log('Projects refreshed successfully');
        },
        onError: (error) => {
          console.error('Failed to refresh projects:', error.message);
        },
        onTimeout: () => {
          console.warn('Project refresh timed out');
        },
      },
      (state) => set(state)
    );
  },
  
  async ensureWorkspace(projectPath: string) {
    return StoreOperationManager.executeWithTimeout(
      async () => {
        await (window as any).ecocode.createWorkspace(projectPath);
        await get().refreshProjects();
      },
      {
        operation: 'ensureWorkspace',
        timeout: 20000,
        onSuccess: () => {
          console.log('Workspace created successfully');
        },
        onError: (error) => {
          console.error('Failed to create workspace:', error.message);
        },
        onTimeout: () => {
          console.warn('Workspace creation timed out');
        },
      },
      (state) => set(state)
    );
  },
  
  async hydrateHealth() {
    await StoreOperationManager.executeWithTimeout(
      async () => {
        const health = await (window as any).ecocode.fetchHealth();
        set({ health });
      },
      {
        operation: 'hydrateHealth',
        timeout: 10000,
        onSuccess: () => {
          console.log('Health status updated successfully');
        },
        onError: (error) => {
          console.error('Failed to fetch health status:', error.message);
          // Set a default health state on error
          set({ 
            health: { 
              status: 'error', 
              version: 'unknown', 
              timestamp: new Date().toISOString() 
            } 
          });
        },
        onTimeout: () => {
          console.warn('Health check timed out');
        },
      },
      (state) => set(state)
    );
  },
  
  clearError() {
    set({ error: StoreOperationManager.createSuccessState() });
  },
  
  async retryLastOperation() {
    const { error } = get();
    if (!error.operation) {
      console.warn('No operation to retry');
      return;
    }
    
    console.log(`Retrying operation: ${error.operation}`);
    
    switch (error.operation) {
      case 'refreshProjects':
        return get().refreshProjects();
      case 'hydrateHealth':
        return get().hydrateHealth();
      default:
        console.warn(`Unknown operation to retry: ${error.operation}`);
    }
  },
  
  cleanup() {
    StoreOperationManager.cleanup();
  },
}));
