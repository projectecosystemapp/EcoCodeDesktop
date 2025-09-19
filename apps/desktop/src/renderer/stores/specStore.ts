import { create } from 'zustand';
import { StoreOperationManager, LoadingState, ErrorState } from '../../shared/storeUtils';
import type { SpecificationWorkflow, SpecSummary } from '../../shared/types';
import type {
  CreateSpecRequest,
  UpdateDocumentRequest,
  ExecuteTaskRequest,
  UpdateTaskStatusRequest,
  ApprovePhaseRequest,
} from '../../main/orchestrator-client';

interface SpecState {
  // State
  specs: SpecSummary[];
  selectedSpec: SpecificationWorkflow | null;
  loading: LoadingState;
  error: ErrorState;
  
  // Actions
  loadSpecs: () => Promise<void>;
  createSpec: (request: CreateSpecRequest) => Promise<string>;
  selectSpec: (specId: string) => Promise<void>;
  refreshSelectedSpec: () => Promise<void>;
  
  // Document operations
  updateRequirements: (specId: string, content: string, approve?: boolean, feedback?: string) => Promise<void>;
  updateDesign: (specId: string, content: string, approve?: boolean, feedback?: string) => Promise<void>;
  updateTasks: (specId: string, content: string, approve?: boolean, feedback?: string) => Promise<void>;
  
  // Approval operations
  approvePhase: (specId: string, phase: string, approved: boolean, feedback?: string) => Promise<void>;
  
  // Task operations
  executeTask: (specId: string, taskId: string) => Promise<void>;
  updateTaskStatus: (specId: string, taskId: string, status: string) => Promise<void>;
  
  // Utility
  clearError: () => void;
  retryLastOperation: () => Promise<void>;
  cleanup: () => void;
}

export const useSpecStore = create<SpecState>((set, get) => ({
  // Initial state
  specs: [],
  selectedSpec: null,
  loading: StoreOperationManager.createIdleState(),
  error: StoreOperationManager.createSuccessState(),

  // Load all specs
  loadSpecs: async () => {
    await StoreOperationManager.executeWithTimeout(
      async () => {
        const specs = await (window as any).ecocode.specs.list();
        set({ specs });
      },
      {
        operation: 'loadSpecs',
        timeout: 15000,
      },
      (state) => set(state)
    );
  },

  // Create new spec
  createSpec: async (request: CreateSpecRequest) => {
    return StoreOperationManager.executeWithTimeout(
      async () => {
        const result = await (window as any).ecocode.specs.create(request);
        await get().loadSpecs(); // Refresh the list
        return result.id;
      },
      {
        operation: 'createSpec',
        timeout: 30000,
      },
      (state) => set(state)
    );
  },

  // Select and load a specific spec
  selectSpec: async (specId: string) => {
    await StoreOperationManager.executeWithTimeout(
      async () => {
        const spec = await (window as any).ecocode.specs.get(specId);
        set({ selectedSpec: spec });
      },
      {
        operation: 'selectSpec',
        timeout: 15000,
      },
      (state) => set(state)
    );
  },

  // Refresh the currently selected spec
  refreshSelectedSpec: async () => {
    const { selectedSpec } = get();
    if (selectedSpec) {
      await get().selectSpec(selectedSpec.id);
    }
  },

  // Update requirements document
  updateRequirements: async (specId: string, content: string, approve?: boolean, feedback?: string) => {
    return StoreOperationManager.executeWithTimeout(
      async () => {
        const request: UpdateDocumentRequest = {
          content,
          approve,
          feedback,
        };
        await (window as any).ecocode.specs.updateRequirements(specId, request);
        await get().refreshSelectedSpec();
        await get().loadSpecs(); // Refresh the list to update status
      },
      {
        operation: 'updateRequirements',
        timeout: 25000,
      },
      (state) => set(state)
    );
  },

  // Update design document
  updateDesign: async (specId: string, content: string, approve?: boolean, feedback?: string) => {
    return StoreOperationManager.executeWithTimeout(
      async () => {
        const request: UpdateDocumentRequest = {
          content,
          approve,
          feedback,
        };
        await (window as any).ecocode.specs.updateDesign(specId, request);
        await get().refreshSelectedSpec();
        await get().loadSpecs();
      },
      {
        operation: 'updateDesign',
        timeout: 25000,
      },
      (state) => set(state)
    );
  },

  // Update tasks document
  updateTasks: async (specId: string, content: string, approve?: boolean, feedback?: string) => {
    return StoreOperationManager.executeWithTimeout(
      async () => {
        const request: UpdateDocumentRequest = {
          content,
          approve,
          feedback,
        };
        await (window as any).ecocode.specs.updateTasks(specId, request);
        await get().refreshSelectedSpec();
        await get().loadSpecs();
      },
      {
        operation: 'updateTasks',
        timeout: 25000,
      },
      (state) => set(state)
    );
  },

  // Approve or reject a phase
  approvePhase: async (specId: string, phase: string, approved: boolean, feedback?: string) => {
    return StoreOperationManager.executeWithTimeout(
      async () => {
        const request: ApprovePhaseRequest = {
          approved,
          feedback,
        };
        await (window as any).ecocode.specs.approvePhase(specId, phase, request);
        await get().refreshSelectedSpec();
        await get().loadSpecs();
      },
      {
        operation: 'approvePhase',
        timeout: 20000,
      },
      (state) => set(state)
    );
  },

  // Execute a task
  executeTask: async (specId: string, taskId: string) => {
    return StoreOperationManager.executeWithTimeout(
      async () => {
        const request: ExecuteTaskRequest = {};
        await (window as any).ecocode.specs.executeTask(specId, taskId, request);
        await get().refreshSelectedSpec();
      },
      {
        operation: 'executeTask',
        timeout: 60000, // Tasks can take longer
      },
      (state) => set(state)
    );
  },

  // Update task status
  updateTaskStatus: async (specId: string, taskId: string, status: string) => {
    return StoreOperationManager.executeWithTimeout(
      async () => {
        const request: UpdateTaskStatusRequest = { status };
        await (window as any).ecocode.specs.updateTaskStatus(specId, taskId, request);
        await get().refreshSelectedSpec();
      },
      {
        operation: 'updateTaskStatus',
        timeout: 15000,
      },
      (state) => set(state)
    );
  },

  // Utility functions
  clearError: () => set({ error: StoreOperationManager.createSuccessState() }),
  
  retryLastOperation: async () => {
    const { error, selectedSpec } = get();
    if (!error.operation) {
      console.warn('No operation to retry');
      return;
    }
    
    console.log(`Retrying operation: ${error.operation}`);
    
    switch (error.operation) {
      case 'loadSpecs':
        return get().loadSpecs();
      case 'selectSpec':
        if (selectedSpec) {
          return get().selectSpec(selectedSpec.id);
        }
        break;
      case 'refreshSelectedSpec':
        return get().refreshSelectedSpec();
      default:
        console.warn(`Cannot retry operation: ${error.operation}`);
    }
  },
  
  cleanup: () => {
    StoreOperationManager.cleanup();
  },
}));