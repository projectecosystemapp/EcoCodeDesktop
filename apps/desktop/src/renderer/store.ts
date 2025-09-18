import { create } from 'zustand';

import type { HealthResponse, ProjectInfo } from '../shared/types';

type AppState = {
  projects: ProjectInfo[];
  health: HealthResponse | null;
  loading: boolean;
  error: string | null;
  refreshProjects: () => Promise<void>;
  ensureWorkspace: (projectPath: string) => Promise<void>;
  hydrateHealth: () => Promise<void>;
};

export const useAppStore = create<AppState>((set, get) => ({
  projects: [],
  health: null,
  loading: false,
  error: null,
  async refreshProjects() {
    set({ loading: true, error: null });
    try {
      const projects = await window.ecocode.listProjects();
      set({ projects });
    } catch (error: unknown) {
      set({ error: error instanceof Error ? error.message : 'Failed to load projects' });
    } finally {
      set({ loading: false });
    }
  },
  async ensureWorkspace(projectPath: string) {
    set({ loading: true, error: null });
    try {
      await window.ecocode.createWorkspace(projectPath);
      await get().refreshProjects();
    } catch (error: unknown) {
      set({ error: error instanceof Error ? error.message : 'Failed to create workspace' });
    } finally {
      set({ loading: false });
    }
  },
  async hydrateHealth() {
    try {
      const health = await window.ecocode.fetchHealth();
      set({ health });
    } catch (error: unknown) {
      set({ error: error instanceof Error ? error.message : 'Failed to reach orchestrator' });
    }
  },
}));
