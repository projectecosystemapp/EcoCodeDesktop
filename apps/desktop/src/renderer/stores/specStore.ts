import { create } from 'zustand';
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
  loading: boolean;
  error: string | null;
  
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
  setLoading: (loading: boolean) => void;
}

export const useSpecStore = create<SpecState>((set, get) => ({
  // Initial state
  specs: [],
  selectedSpec: null,
  loading: false,
  error: null,

  // Load all specs
  loadSpecs: async () => {
    set({ loading: true, error: null });
    try {
      const specs = await window.ecocode.specs.list();
      set({ specs, loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to load specs',
        loading: false 
      });
    }
  },

  // Create new spec
  createSpec: async (request: CreateSpecRequest) => {
    set({ loading: true, error: null });
    try {
      const result = await window.ecocode.specs.create(request);
      await get().loadSpecs(); // Refresh the list
      set({ loading: false });
      return result.id;
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to create spec',
        loading: false 
      });
      throw error;
    }
  },

  // Select and load a specific spec
  selectSpec: async (specId: string) => {
    set({ loading: true, error: null });
    try {
      const spec = await window.ecocode.specs.get(specId);
      set({ selectedSpec: spec, loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to load spec',
        loading: false 
      });
    }
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
    set({ loading: true, error: null });
    try {
      const request: UpdateDocumentRequest = {
        content,
        approve,
        feedback,
      };
      await window.ecocode.specs.updateRequirements(specId, request);
      await get().refreshSelectedSpec();
      await get().loadSpecs(); // Refresh the list to update status
      set({ loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to update requirements',
        loading: false 
      });
      throw error;
    }
  },

  // Update design document
  updateDesign: async (specId: string, content: string, approve?: boolean, feedback?: string) => {
    set({ loading: true, error: null });
    try {
      const request: UpdateDocumentRequest = {
        content,
        approve,
        feedback,
      };
      await window.ecocode.specs.updateDesign(specId, request);
      await get().refreshSelectedSpec();
      await get().loadSpecs();
      set({ loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to update design',
        loading: false 
      });
      throw error;
    }
  },

  // Update tasks document
  updateTasks: async (specId: string, content: string, approve?: boolean, feedback?: string) => {
    set({ loading: true, error: null });
    try {
      const request: UpdateDocumentRequest = {
        content,
        approve,
        feedback,
      };
      await window.ecocode.specs.updateTasks(specId, request);
      await get().refreshSelectedSpec();
      await get().loadSpecs();
      set({ loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to update tasks',
        loading: false 
      });
      throw error;
    }
  },

  // Approve or reject a phase
  approvePhase: async (specId: string, phase: string, approved: boolean, feedback?: string) => {
    set({ loading: true, error: null });
    try {
      const request: ApprovePhaseRequest = {
        approved,
        feedback,
      };
      await window.ecocode.specs.approvePhase(specId, phase, request);
      await get().refreshSelectedSpec();
      await get().loadSpecs();
      set({ loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to process approval',
        loading: false 
      });
      throw error;
    }
  },

  // Execute a task
  executeTask: async (specId: string, taskId: string) => {
    set({ loading: true, error: null });
    try {
      const request: ExecuteTaskRequest = {};
      await window.ecocode.specs.executeTask(specId, taskId, request);
      await get().refreshSelectedSpec();
      set({ loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to execute task',
        loading: false 
      });
      throw error;
    }
  },

  // Update task status
  updateTaskStatus: async (specId: string, taskId: string, status: string) => {
    set({ loading: true, error: null });
    try {
      const request: UpdateTaskStatusRequest = { status };
      await window.ecocode.specs.updateTaskStatus(specId, taskId, request);
      await get().refreshSelectedSpec();
      set({ loading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Failed to update task status',
        loading: false 
      });
      throw error;
    }
  },

  // Utility functions
  clearError: () => set({ error: null }),
  setLoading: (loading: boolean) => set({ loading }),
}));