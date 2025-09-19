import { useEffect, useState } from 'react';

import {
  ActionIcon,
  AppShell,
  Badge,
  Button,
  Group,
  Loader,
  Notification,
  ScrollArea,
  Stack,
  Text,
  Title,
  Tabs,
} from '@mantine/core';
import { IconRefresh, IconShieldCheck, IconShieldX, IconFileText, IconSettings } from '@tabler/icons-react';

import type { ProjectInfo } from '../shared/types';
import { useAppStore } from './store';
import { getLoadingCompat, getErrorMessage } from '../shared/storeCompat';
import { SpecWorkflow } from './components';

function ProjectList({
  projects,
  onEnsureWorkspace,
  onSelect,
  activePath,
}: {
  projects: ProjectInfo[];
  onEnsureWorkspace: (projectPath: string) => Promise<void>;
  onSelect: (project: ProjectInfo) => void;
  activePath: string | null;
}) {
  return (
    <Stack gap="xs" p="sm">
      {projects.map((project) => {
        const isActive = activePath === project.path;
        return (
          <Stack
            key={project.path}
            p="sm"
            style={{
              borderRadius: 8,
              border: isActive ? '1px solid var(--mantine-color-blue-5)' : '1px solid rgba(255,255,255,0.08)',
              backgroundColor: isActive ? 'rgba(59, 130, 246, 0.12)' : 'transparent',
              cursor: 'pointer',
            }}
            gap="xs"
            onClick={() => onSelect(project)}
          >
            <Group justify="space-between">
              <Stack gap={2}>
                <Text fw={600}>{project.name}</Text>
                <Text size="xs" c="dimmed">
                  {project.path}
                </Text>
              </Stack>
              <Group gap="xs">
                {project.has_workspace ? (
                  <Badge color="teal" variant="light">
                    Workspace Ready
                  </Badge>
                ) : (
                  <Button size="xs" onClick={(event) => {
                    event.stopPropagation();
                    void onEnsureWorkspace(project.path);
                  }}>
                    Initialize
                  </Button>
                )}
              </Group>
            </Group>
          </Stack>
        );
      })}
    </Stack>
  );
}

function ProjectDetails({ project }: { project: ProjectInfo | null }) {
  if (!project) {
    return (
      <Stack align="center" justify="center" h="100%">
        <Text size="lg" c="dimmed">
          Select a project to inspect its workspace status.
        </Text>
      </Stack>
    );
  }

  return (
    <Stack p="xl" gap="xl">
      <Stack gap="xs">
        <Title order={2}>{project.name}</Title>
        <Text size="sm" c="dimmed">
          {project.path}
        </Text>
      </Stack>
      <Group gap="sm">
        <Text fw={500}>Workspace status:</Text>
        {project.has_workspace ? (
          <Badge color="teal" leftSection={<IconShieldCheck size={16} />}>
            Encrypted workspace present
          </Badge>
        ) : (
          <Badge color="red" leftSection={<IconShieldX size={16} />}>
            Workspace missing
          </Badge>
        )}
      </Group>
      {project.workspace_path && (
        <Stack gap="xs">
          <Text fw={500}>Workspace location</Text>
          <Text size="sm" c="dimmed">
            {project.workspace_path}
          </Text>
        </Stack>
      )}
    </Stack>
  );
}

export function App() {
  const projects = useAppStore((state) => state.projects);
  const refreshProjects = useAppStore((state) => state.refreshProjects);
  const ensureWorkspace = useAppStore((state) => state.ensureWorkspace);
  const loadingState = useAppStore((state) => state.loading);
  const errorState = useAppStore((state) => state.error);
  const health = useAppStore((state) => state.health);
  const hydrateHealth = useAppStore((state) => state.hydrateHealth);
  
  const loading = getLoadingCompat(loadingState);
  const error = getErrorMessage(errorState);

  const [selectedProject, setSelectedProject] = useState<ProjectInfo | null>(null);
  const [activeTab, setActiveTab] = useState<string>('workspaces');

  useEffect(() => {
    void refreshProjects();
    void hydrateHealth();
  }, [refreshProjects, hydrateHealth]);

  useEffect(() => {
    if (selectedProject) {
      const updated = projects.find((project) => project.path === selectedProject.path);
      if (updated) {
        setSelectedProject(updated);
      }
    }
  }, [projects, selectedProject]);

  return (
    <AppShell
      padding="0"
      header={{ height: 64 }}
      navbar={{ width: 360, breakpoint: 'sm' }}
      styles={{
        main: {
          background: '#05070b',
          color: '#f6f7fb',
        },
        navbar: {
          borderRight: '1px solid rgba(255,255,255,0.08)',
          background: '#10131a',
        },
        header: {
          borderBottom: '1px solid rgba(255,255,255,0.08)',
          background: '#10131a',
        },
      }}
    >
      <AppShell.Header p="md">
        <Group justify="space-between">
          <Stack gap={2}>
            <Title order={3} c="white">
              EcoCode Workspace Manager
            </Title>
            <Text size="xs" c="dimmed">
              Secure spec-driven development orchestration
            </Text>
          </Stack>
          <Group gap="sm">
            {health ? (
              <Badge color="teal" variant="light">
                {health.status.toUpperCase()} · v{health.version}
              </Badge>
            ) : (
              <Badge color="yellow" variant="light">
                Checking orchestrator…
              </Badge>
            )}
            <ActionIcon
              variant="light"
              color="blue"
              onClick={() => {
                void refreshProjects();
                void hydrateHealth();
              }}
              aria-label="Refresh"
            >
              <IconRefresh size={18} />
            </ActionIcon>
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar>
        <ScrollArea style={{ height: '100%' }}>
          {loading && (
            <Group justify="center" p="md">
              <Loader size="sm" color="blue" />
            </Group>
          )}
          <ProjectList
            projects={projects}
            onEnsureWorkspace={(path) => ensureWorkspace(path)}
            onSelect={(project) => setSelectedProject(project)}
            activePath={selectedProject?.path ?? null}
          />
        </ScrollArea>
      </AppShell.Navbar>
      <AppShell.Main>
        {error && (
          <Notification color="red" withCloseButton={false} p="md">
            {error}
          </Notification>
        )}
        <Tabs value={activeTab} onChange={(value) => setActiveTab(value || 'workspaces')} p="md">
          <Tabs.List>
            <Tabs.Tab value="workspaces" leftSection={<IconSettings size={16} />}>
              Workspaces
            </Tabs.Tab>
            <Tabs.Tab value="specs" leftSection={<IconFileText size={16} />}>
              Spec Workflows
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="workspaces" pt="md">
            <ProjectDetails project={selectedProject} />
          </Tabs.Panel>

          <Tabs.Panel value="specs" pt="md">
            <SpecWorkflow />
          </Tabs.Panel>
        </Tabs>
      </AppShell.Main>
    </AppShell>
  );
}
