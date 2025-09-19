import { useState, useEffect } from 'react';
import {
  Button,
  Group,
  Stack,
  Text,
  Title,
  Progress,
  Badge,
  Alert,
  Accordion,
  ActionIcon,
  Tooltip,
  ScrollArea,
  Card,
  Divider,
} from '@mantine/core';
import {
  IconAlertCircle,
  IconCheck,
  IconClock,
  IconPlayerPlay,
  IconRefresh,
  IconX,
  IconChevronRight,
} from '@tabler/icons-react';
import type {
  ExecuteTaskRequest,
  ExecuteTaskResponse,
  UpdateTaskStatusRequest,
  ProgressResponse,
} from '../../main/orchestrator-client';
import type { Task } from '../../shared/types';
import { TaskStatus } from '../../shared/types';

interface TaskExecutionPanelProps {
  specId: string;
  tasks: Task[];
  onExecuteTask: (taskId: string, request: ExecuteTaskRequest) => Promise<ExecuteTaskResponse>;
  onUpdateTaskStatus: (taskId: string, request: UpdateTaskStatusRequest) => Promise<void>;
  onRefreshProgress: () => Promise<ProgressResponse>;
}

interface TaskItemProps {
  task: Task;
  level: number;
  onExecute: (taskId: string) => void;
  onUpdateStatus: (taskId: string, status: TaskStatus) => void;
  loading: boolean;
}

function TaskItem({ task, level, onExecute, onUpdateStatus, loading }: TaskItemProps) {
  const getStatusColor = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.COMPLETED:
        return 'teal';
      case TaskStatus.IN_PROGRESS:
        return 'blue';
      case TaskStatus.BLOCKED:
        return 'red';
      default:
        return 'gray';
    }
  };

  const getStatusIcon = (status: TaskStatus) => {
    switch (status) {
      case TaskStatus.COMPLETED:
        return <IconCheck size={16} />;
      case TaskStatus.IN_PROGRESS:
        return <IconClock size={16} />;
      case TaskStatus.BLOCKED:
        return <IconX size={16} />;
      default:
        return <IconChevronRight size={16} />;
    }
  };

  const canExecute = task.status === TaskStatus.NOT_STARTED || task.status === TaskStatus.BLOCKED;
  const canMarkComplete = task.status === TaskStatus.IN_PROGRESS;

  return (
    <Card
      padding="sm"
      style={{
        marginLeft: level * 20,
        marginBottom: 8,
        border: `1px solid var(--mantine-color-${getStatusColor(task.status)}-3)`,
      }}
    >
      <Group justify="space-between" align="flex-start">
        <Stack gap="xs" style={{ flex: 1 }}>
          <Group gap="sm">
            <Badge
              color={getStatusColor(task.status)}
              leftSection={getStatusIcon(task.status)}
              variant="light"
            >
              {task.status.replace('_', ' ').toUpperCase()}
            </Badge>
            <Text fw={500} size="sm">
              {task.description}
            </Text>
          </Group>
          
          {task.requirements.length > 0 && (
            <Text size="xs" c="dimmed">
              Requirements: {task.requirements.join(', ')}
            </Text>
          )}
          
          {task.dependencies.length > 0 && (
            <Text size="xs" c="dimmed">
              Dependencies: {task.dependencies.join(', ')}
            </Text>
          )}
        </Stack>
        
        <Group gap="xs">
          {canExecute && (
            <Tooltip label="Execute task">
              <ActionIcon
                color="blue"
                variant="light"
                onClick={() => onExecute(task.id)}
                loading={loading}
                size="sm"
              >
                <IconPlayerPlay size={14} />
              </ActionIcon>
            </Tooltip>
          )}
          
          {canMarkComplete && (
            <Tooltip label="Mark as complete">
              <ActionIcon
                color="teal"
                variant="light"
                onClick={() => onUpdateStatus(task.id, TaskStatus.COMPLETED)}
                loading={loading}
                size="sm"
              >
                <IconCheck size={14} />
              </ActionIcon>
            </Tooltip>
          )}
        </Group>
      </Group>
      
      {task.subtasks.length > 0 && (
        <Stack gap="xs" mt="sm">
          <Divider />
          {task.subtasks.map((subtask) => (
            <TaskItem
              key={subtask.id}
              task={subtask}
              level={level + 1}
              onExecute={onExecute}
              onUpdateStatus={onUpdateStatus}
              loading={loading}
            />
          ))}
        </Stack>
      )}
    </Card>
  );
}

export function TaskExecutionPanel({
  specId,
  tasks,
  onExecuteTask,
  onUpdateTaskStatus,
  onRefreshProgress,
}: TaskExecutionPanelProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [progress, setProgress] = useState<ProgressResponse | null>(null);
  const [executionLog, setExecutionLog] = useState<string[]>([]);

  useEffect(() => {
    loadProgress();
  }, [specId]);

  const loadProgress = async () => {
    try {
      const progressData = await onRefreshProgress();
      setProgress(progressData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load progress');
    }
  };

  const handleExecuteTask = async (taskId: string) => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const request: ExecuteTaskRequest = {};
      const result = await onExecuteTask(taskId, request);
      
      if (result.success) {
        setSuccess(result.message);
        setExecutionLog(result.execution_log);
        await loadProgress();
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to execute task');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateStatus = async (taskId: string, status: TaskStatus) => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const request: UpdateTaskStatusRequest = { status };
      await onUpdateTaskStatus(taskId, request);
      setSuccess(`Task status updated to ${status}`);
      await loadProgress();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update task status');
    } finally {
      setLoading(false);
    }
  };

  const progressPercentage = progress ? progress.progress_percentage : 0;
  const completedTasks = progress ? progress.completed_tasks : 0;
  const totalTasks = progress ? progress.total_tasks : tasks.length;

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center">
        <Title order={3}>Task Execution</Title>
        <Group gap="sm">
          <Badge color="blue" variant="light">
            {completedTasks} / {totalTasks} Complete
          </Badge>
          <Tooltip label="Refresh progress">
            <ActionIcon
              variant="light"
              color="blue"
              onClick={loadProgress}
              loading={loading}
            >
              <IconRefresh size={16} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      <Stack gap="xs">
        <Group justify="space-between">
          <Text size="sm" fw={500}>
            Overall Progress
          </Text>
          <Text size="sm" c="dimmed">
            {Math.round(progressPercentage)}%
          </Text>
        </Group>
        <Progress value={progressPercentage} size="lg" />
      </Stack>

      {progress && (
        <Group gap="md">
          <Badge color="gray" variant="light">
            Not Started: {progress.not_started_tasks}
          </Badge>
          <Badge color="blue" variant="light">
            In Progress: {progress.in_progress_tasks}
          </Badge>
          <Badge color="teal" variant="light">
            Completed: {progress.completed_tasks}
          </Badge>
          {progress.blocked_tasks > 0 && (
            <Badge color="red" variant="light">
              Blocked: {progress.blocked_tasks}
            </Badge>
          )}
        </Group>
      )}

      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert icon={<IconCheck size={16} />} color="teal" onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <ScrollArea style={{ height: '400px' }}>
        <Stack gap="xs">
          {tasks.map((task) => (
            <TaskItem
              key={task.id}
              task={task}
              level={0}
              onExecute={handleExecuteTask}
              onUpdateStatus={handleUpdateStatus}
              loading={loading}
            />
          ))}
        </Stack>
      </ScrollArea>

      {executionLog.length > 0 && (
        <Accordion variant="contained">
          <Accordion.Item value="execution-log">
            <Accordion.Control>Execution Log</Accordion.Control>
            <Accordion.Panel>
              <ScrollArea style={{ height: '200px' }}>
                <Stack gap="xs">
                  {executionLog.map((logEntry, index) => (
                    <Text key={index} size="xs" style={{ fontFamily: 'monospace' }}>
                      {logEntry}
                    </Text>
                  ))}
                </Stack>
              </ScrollArea>
            </Accordion.Panel>
          </Accordion.Item>
        </Accordion>
      )}
    </Stack>
  );
}