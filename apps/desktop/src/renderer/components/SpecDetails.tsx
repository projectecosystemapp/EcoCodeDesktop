import { useState, useEffect } from 'react';
import {
  Stack,
  Text,
  Title,
  Badge,
  Group,
  Tabs,
  ScrollArea,
  Alert,
  Loader,
  Button,
  ActionIcon,
  Tooltip,
  Card,
  Progress,
  Divider,
} from '@mantine/core';
import {
  IconAlertCircle,
  IconCheck,
  IconRefresh,
  IconFileText,
  IconSettings,
  IconListCheck,
  IconPlayerPlay,
  IconEye,
} from '@tabler/icons-react';
import type { SpecificationWorkflow, WorkflowStatus } from '../../shared/types';
import { WorkflowPhase } from '../../shared/types';
import { DocumentEditor } from './DocumentEditor';
import { TaskExecutionPanel } from './TaskExecutionPanel';

interface SpecDetailsProps {
  spec: SpecificationWorkflow | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => Promise<void>;
  onUpdateDocument: (documentType: 'requirements' | 'design' | 'tasks', content: string) => Promise<void>;
  onApprovePhase: (phase: string, approved: boolean, feedback?: string) => Promise<void>;
  onExecuteTask: (taskId: string) => Promise<void>;
  onUpdateTaskStatus: (taskId: string, status: string) => Promise<void>;
}

export function SpecDetails({
  spec,
  loading,
  error,
  onRefresh,
  onUpdateDocument,
  onApprovePhase,
  onExecuteTask,
  onUpdateTaskStatus,
}: SpecDetailsProps) {
  const [activeTab, setActiveTab] = useState<string>('overview');

  useEffect(() => {
    if (spec) {
      // Auto-select appropriate tab based on current phase
      switch (spec.currentPhase) {
        case WorkflowPhase.REQUIREMENTS:
          setActiveTab('requirements');
          break;
        case WorkflowPhase.DESIGN:
          setActiveTab('design');
          break;
        case WorkflowPhase.TASKS:
          setActiveTab('tasks');
          break;
        case WorkflowPhase.EXECUTION:
          setActiveTab('execution');
          break;
        default:
          setActiveTab('overview');
      }
    }
  }, [spec?.id, spec?.currentPhase]);

  if (loading && !spec) {
    return (
      <Stack align="center" justify="center" h="100%" gap="md">
        <Loader size="lg" />
        <Text c="dimmed">Loading specification...</Text>
      </Stack>
    );
  }

  if (error) {
    return (
      <Stack align="center" justify="center" h="100%" gap="md">
        <Alert icon={<IconAlertCircle size={16} />} color="red" style={{ maxWidth: '400px' }}>
          {error}
        </Alert>
        <Button onClick={onRefresh} variant="light">
          Try Again
        </Button>
      </Stack>
    );
  }

  if (!spec) {
    return (
      <Stack align="center" justify="center" h="100%" gap="md">
        <Text size="lg" c="dimmed" ta="center">
          Select a specification from the list to view its details.
        </Text>
      </Stack>
    );
  }

  const getPhaseColor = (phase: WorkflowPhase) => {
    switch (phase) {
      case WorkflowPhase.REQUIREMENTS:
        return 'blue';
      case WorkflowPhase.DESIGN:
        return 'orange';
      case WorkflowPhase.TASKS:
        return 'green';
      case WorkflowPhase.EXECUTION:
        return 'purple';
      default:
        return 'gray';
    }
  };

  const getStatusColor = (status: WorkflowStatus) => {
    switch (status) {
      case 'completed':
        return 'teal';
      case 'in_progress':
        return 'blue';
      case 'approved':
        return 'green';
      case 'error':
        return 'red';
      default:
        return 'gray';
    }
  };

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const getPhaseProgress = () => {
    const phases = [WorkflowPhase.REQUIREMENTS, WorkflowPhase.DESIGN, WorkflowPhase.TASKS, WorkflowPhase.EXECUTION];
    const currentIndex = phases.indexOf(spec.currentPhase);
    return ((currentIndex + 1) / phases.length) * 100;
  };

  return (
    <Stack gap="md" h="100%">
      <Group justify="space-between" align="center">
        <Stack gap="xs">
          <Group gap="sm">
            <Title order={2}>{spec.featureName}</Title>
            <Badge
              color={getPhaseColor(spec.currentPhase)}
              variant="light"
            >
              {spec.currentPhase.charAt(0).toUpperCase() + spec.currentPhase.slice(1)} Phase
            </Badge>
            <Badge
              color={getStatusColor(spec.status)}
              variant="dot"
            >
              {spec.status.replace('_', ' ').toUpperCase()}
            </Badge>
          </Group>
          <Text size="sm" c="dimmed">
            ID: {spec.id}
          </Text>
        </Stack>
        
        <Tooltip label="Refresh specification">
          <ActionIcon
            variant="light"
            color="blue"
            onClick={onRefresh}
            loading={loading}
          >
            <IconRefresh size={16} />
          </ActionIcon>
        </Tooltip>
      </Group>

      <Card padding="md">
        <Stack gap="sm">
          <Group justify="space-between">
            <Text fw={500}>Workflow Progress</Text>
            <Text size="sm" c="dimmed">
              {Math.round(getPhaseProgress())}% Complete
            </Text>
          </Group>
          <Progress value={getPhaseProgress()} size="lg" />
          <Group gap="md" mt="xs">
            <Badge
              color={spec.currentPhase === WorkflowPhase.REQUIREMENTS ? 'blue' : spec.approvals.requirements?.approved ? 'teal' : 'gray'}
              variant={spec.currentPhase === WorkflowPhase.REQUIREMENTS ? 'filled' : 'light'}
              leftSection={spec.approvals.requirements?.approved ? <IconCheck size={12} /> : undefined}
            >
              Requirements
            </Badge>
            <Badge
              color={spec.currentPhase === WorkflowPhase.DESIGN ? 'orange' : spec.approvals.design?.approved ? 'teal' : 'gray'}
              variant={spec.currentPhase === WorkflowPhase.DESIGN ? 'filled' : 'light'}
              leftSection={spec.approvals.design?.approved ? <IconCheck size={12} /> : undefined}
            >
              Design
            </Badge>
            <Badge
              color={spec.currentPhase === WorkflowPhase.TASKS ? 'green' : spec.approvals.tasks?.approved ? 'teal' : 'gray'}
              variant={spec.currentPhase === WorkflowPhase.TASKS ? 'filled' : 'light'}
              leftSection={spec.approvals.tasks?.approved ? <IconCheck size={12} /> : undefined}
            >
              Tasks
            </Badge>
            <Badge
              color={spec.currentPhase === WorkflowPhase.EXECUTION ? 'purple' : 'gray'}
              variant={spec.currentPhase === WorkflowPhase.EXECUTION ? 'filled' : 'light'}
            >
              Execution
            </Badge>
          </Group>
        </Stack>
      </Card>

      <Tabs value={activeTab} onChange={(value) => setActiveTab(value || 'overview')} style={{ flex: 1 }}>
        <Tabs.List>
          <Tabs.Tab value="overview" leftSection={<IconEye size={16} />}>
            Overview
          </Tabs.Tab>
          <Tabs.Tab value="requirements" leftSection={<IconFileText size={16} />}>
            Requirements
          </Tabs.Tab>
          <Tabs.Tab value="design" leftSection={<IconSettings size={16} />}>
            Design
          </Tabs.Tab>
          <Tabs.Tab value="tasks" leftSection={<IconListCheck size={16} />}>
            Tasks
          </Tabs.Tab>
          <Tabs.Tab value="execution" leftSection={<IconPlayerPlay size={16} />}>
            Execution
          </Tabs.Tab>
        </Tabs.List>

        <ScrollArea style={{ flex: 1 }} mt="md">
          <Tabs.Panel value="overview">
            <Stack gap="md">
              <Card padding="md">
                <Stack gap="sm">
                  <Text fw={500}>Specification Metadata</Text>
                  <Divider />
                  <Group justify="space-between">
                    <Text size="sm">Created:</Text>
                    <Text size="sm" c="dimmed">{formatDate(spec.metadata.createdAt)}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Last Updated:</Text>
                    <Text size="sm" c="dimmed">{formatDate(spec.metadata.updatedAt)}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Version:</Text>
                    <Text size="sm" c="dimmed">{spec.metadata.version}</Text>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Created By:</Text>
                    <Text size="sm" c="dimmed">{spec.metadata.createdBy}</Text>
                  </Group>
                </Stack>
              </Card>

              <Card padding="md">
                <Stack gap="sm">
                  <Text fw={500}>Approval Status</Text>
                  <Divider />
                  <Group justify="space-between">
                    <Text size="sm">Requirements:</Text>
                    <Badge
                      color={spec.approvals.requirements?.approved ? 'teal' : 'gray'}
                      variant="light"
                      leftSection={spec.approvals.requirements?.approved ? <IconCheck size={12} /> : undefined}
                    >
                      {spec.approvals.requirements?.approved ? 'Approved' : 'Pending'}
                    </Badge>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Design:</Text>
                    <Badge
                      color={spec.approvals.design?.approved ? 'teal' : 'gray'}
                      variant="light"
                      leftSection={spec.approvals.design?.approved ? <IconCheck size={12} /> : undefined}
                    >
                      {spec.approvals.design?.approved ? 'Approved' : 'Pending'}
                    </Badge>
                  </Group>
                  <Group justify="space-between">
                    <Text size="sm">Tasks:</Text>
                    <Badge
                      color={spec.approvals.tasks?.approved ? 'teal' : 'gray'}
                      variant="light"
                      leftSection={spec.approvals.tasks?.approved ? <IconCheck size={12} /> : undefined}
                    >
                      {spec.approvals.tasks?.approved ? 'Approved' : 'Pending'}
                    </Badge>
                  </Group>
                </Stack>
              </Card>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="requirements">
            <DocumentEditor
              specId={spec.id}
              documentType="requirements"
              phase={WorkflowPhase.REQUIREMENTS}
              content={spec.documents.requirements ? JSON.stringify(spec.documents.requirements, null, 2) : ''}
              isApproved={spec.approvals.requirements?.approved}
              onUpdate={async (content) => {
                await onUpdateDocument('requirements', content);
                return { success: true, message: 'Requirements updated', updated_at: new Date().toISOString(), checksum: '' };
              }}
              onApprove={async (approved, feedback) => {
                await onApprovePhase('requirements', approved, feedback);
              }}
            />
          </Tabs.Panel>

          <Tabs.Panel value="design">
            <DocumentEditor
              specId={spec.id}
              documentType="design"
              phase={WorkflowPhase.DESIGN}
              content={spec.documents.design ? JSON.stringify(spec.documents.design, null, 2) : ''}
              isApproved={spec.approvals.design?.approved}
              onUpdate={async (content) => {
                await onUpdateDocument('design', content);
                return { success: true, message: 'Design updated', updated_at: new Date().toISOString(), checksum: '' };
              }}
              onApprove={async (approved, feedback) => {
                await onApprovePhase('design', approved, feedback);
              }}
            />
          </Tabs.Panel>

          <Tabs.Panel value="tasks">
            <DocumentEditor
              specId={spec.id}
              documentType="tasks"
              phase={WorkflowPhase.TASKS}
              content={spec.documents.tasks ? JSON.stringify(spec.documents.tasks, null, 2) : ''}
              isApproved={spec.approvals.tasks?.approved}
              onUpdate={async (content) => {
                await onUpdateDocument('tasks', content);
                return { success: true, message: 'Tasks updated', updated_at: new Date().toISOString(), checksum: '' };
              }}
              onApprove={async (approved, feedback) => {
                await onApprovePhase('tasks', approved, feedback);
              }}
            />
          </Tabs.Panel>

          <Tabs.Panel value="execution">
            {spec.documents.tasks ? (
              <TaskExecutionPanel
                specId={spec.id}
                tasks={spec.documents.tasks.tasks}
                onExecuteTask={async (taskId, request) => {
                  await onExecuteTask(taskId);
                  return {
                    success: true,
                    message: 'Task executed',
                    task_id: taskId,
                    status: 'in_progress',
                    execution_log: ['Task execution initiated'],
                  };
                }}
                onUpdateTaskStatus={async (taskId, request) => {
                  await onUpdateTaskStatus(taskId, request.status);
                }}
                onRefreshProgress={async () => {
                  return {
                    spec_id: spec.id,
                    total_tasks: spec.documents.tasks?.tasks.length || 0,
                    completed_tasks: 0,
                    in_progress_tasks: 0,
                    not_started_tasks: spec.documents.tasks?.tasks.length || 0,
                    blocked_tasks: 0,
                    progress_percentage: 0,
                    current_phase: spec.currentPhase,
                    status: spec.status,
                  };
                }}
              />
            ) : (
              <Alert icon={<IconAlertCircle size={16} />} color="yellow">
                Tasks document must be created and approved before execution can begin.
              </Alert>
            )}
          </Tabs.Panel>
        </ScrollArea>
      </Tabs>
    </Stack>
  );
}