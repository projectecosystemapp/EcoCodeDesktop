import { useState, useEffect } from 'react';
import {
  Button,
  Group,
  Stack,
  Text,
  TextInput,
  Badge,
  Card,
  ActionIcon,
  Tooltip,
  Loader,
  Alert,
  Select,
  ScrollArea,
  Title,
} from '@mantine/core';
import {
  IconSearch,
  IconPlus,
  IconRefresh,
  IconEye,
  IconAlertCircle,
  IconFilter,
} from '@tabler/icons-react';
import type { SpecSummary, WorkflowStatus } from '../../shared/types';
import { WorkflowPhase } from '../../shared/types';

interface SpecListProps {
  specs: SpecSummary[];
  loading: boolean;
  error: string | null;
  onRefresh: () => Promise<void>;
  onCreateNew: () => void;
  onSelectSpec: (specId: string) => void;
  selectedSpecId?: string;
}

export function SpecList({
  specs,
  loading,
  error,
  onRefresh,
  onCreateNew,
  onSelectSpec,
  selectedSpecId,
}: SpecListProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [phaseFilter, setPhaseFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const filteredSpecs = specs.filter((spec) => {
    const matchesSearch = spec.featureName.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         spec.id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesPhase = !phaseFilter || spec.currentPhase === phaseFilter;
    const matchesStatus = !statusFilter || spec.status === statusFilter;
    
    return matchesSearch && matchesPhase && matchesStatus;
  });

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
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  return (
    <Stack gap="md" h="100%">
      <Group justify="space-between" align="center">
        <Title order={3}>Specifications</Title>
        <Group gap="sm">
          <Tooltip label="Refresh specs">
            <ActionIcon
              variant="light"
              color="blue"
              onClick={onRefresh}
              loading={loading}
            >
              <IconRefresh size={16} />
            </ActionIcon>
          </Tooltip>
          <Button
            leftSection={<IconPlus size={16} />}
            onClick={onCreateNew}
            size="sm"
          >
            New Spec
          </Button>
        </Group>
      </Group>

      <Stack gap="sm">
        <TextInput
          placeholder="Search specifications..."
          leftSection={<IconSearch size={16} />}
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.currentTarget.value)}
        />
        
        <Group gap="sm">
          <Select
            placeholder="Filter by phase"
            leftSection={<IconFilter size={16} />}
            data={[
              { value: 'requirements', label: 'Requirements' },
              { value: 'design', label: 'Design' },
              { value: 'tasks', label: 'Tasks' },
              { value: 'execution', label: 'Execution' },
            ]}
            value={phaseFilter}
            onChange={setPhaseFilter}
            clearable
            size="sm"
            style={{ flex: 1 }}
          />
          
          <Select
            placeholder="Filter by status"
            leftSection={<IconFilter size={16} />}
            data={[
              { value: 'draft', label: 'Draft' },
              { value: 'in_review', label: 'In Review' },
              { value: 'approved', label: 'Approved' },
              { value: 'in_progress', label: 'In Progress' },
              { value: 'completed', label: 'Completed' },
              { value: 'error', label: 'Error' },
            ]}
            value={statusFilter}
            onChange={setStatusFilter}
            clearable
            size="sm"
            style={{ flex: 1 }}
          />
        </Group>
      </Stack>

      {error && (
        <Alert icon={<IconAlertCircle size={16} />} color="red">
          {error}
        </Alert>
      )}

      <ScrollArea style={{ flex: 1 }}>
        {loading && specs.length === 0 ? (
          <Group justify="center" p="xl">
            <Loader size="sm" />
            <Text c="dimmed">Loading specifications...</Text>
          </Group>
        ) : filteredSpecs.length === 0 ? (
          <Stack align="center" justify="center" p="xl" gap="md">
            <Text c="dimmed" ta="center">
              {specs.length === 0 
                ? 'No specifications found. Create your first spec to get started.'
                : 'No specifications match your filters.'
              }
            </Text>
            {specs.length === 0 && (
              <Button
                leftSection={<IconPlus size={16} />}
                onClick={onCreateNew}
                variant="light"
              >
                Create First Specification
              </Button>
            )}
          </Stack>
        ) : (
          <Stack gap="sm">
            {filteredSpecs.map((spec) => (
              <Card
                key={spec.id}
                padding="md"
                style={{
                  cursor: 'pointer',
                  border: selectedSpecId === spec.id 
                    ? '2px solid var(--mantine-color-blue-5)' 
                    : '1px solid var(--mantine-color-gray-3)',
                  backgroundColor: selectedSpecId === spec.id 
                    ? 'var(--mantine-color-blue-0)' 
                    : undefined,
                }}
                onClick={() => onSelectSpec(spec.id)}
              >
                <Group justify="space-between" align="flex-start">
                  <Stack gap="xs" style={{ flex: 1 }}>
                    <Group gap="sm">
                      <Text fw={600} size="sm">
                        {spec.featureName}
                      </Text>
                      <Badge
                        color={getPhaseColor(spec.currentPhase)}
                        variant="light"
                        size="sm"
                      >
                        {spec.currentPhase.charAt(0).toUpperCase() + spec.currentPhase.slice(1)}
                      </Badge>
                      <Badge
                        color={getStatusColor(spec.status)}
                        variant="dot"
                        size="sm"
                      >
                        {spec.status.replace('_', ' ').toUpperCase()}
                      </Badge>
                    </Group>
                    
                    <Text size="xs" c="dimmed">
                      ID: {spec.id}
                    </Text>
                    
                    <Group gap="sm" align="center">
                      <Text size="xs" c="dimmed">
                        Progress: {Math.round(spec.progress)}%
                      </Text>
                      <div
                        style={{
                          width: '60px',
                          height: '4px',
                          backgroundColor: 'var(--mantine-color-gray-3)',
                          borderRadius: '2px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${spec.progress}%`,
                            height: '100%',
                            backgroundColor: `var(--mantine-color-${getPhaseColor(spec.currentPhase)}-5)`,
                            transition: 'width 0.3s ease',
                          }}
                        />
                      </div>
                    </Group>
                    
                    <Text size="xs" c="dimmed">
                      Last updated: {formatDate(spec.lastUpdated)}
                    </Text>
                  </Stack>
                  
                  <Tooltip label="View details">
                    <ActionIcon
                      variant="light"
                      color="blue"
                      size="sm"
                      onClick={(event) => {
                        event.stopPropagation();
                        onSelectSpec(spec.id);
                      }}
                    >
                      <IconEye size={14} />
                    </ActionIcon>
                  </Tooltip>
                </Group>
              </Card>
            ))}
          </Stack>
        )}
      </ScrollArea>
    </Stack>
  );
}