import { useState } from 'react';
import {
  Modal,
  Stack,
  Text,
  Title,
  Button,
  Group,
  Textarea,
  Alert,
  Badge,
  Divider,
  ScrollArea,
} from '@mantine/core';
import { IconAlertCircle, IconCheck, IconX } from '@tabler/icons-react';
import { WorkflowPhase } from '../../shared/types';

interface ApprovalDialogProps {
  opened: boolean;
  onClose: () => void;
  phase: WorkflowPhase;
  documentContent: string;
  onApprove: (approved: boolean, feedback?: string) => Promise<void>;
  loading?: boolean;
}

export function ApprovalDialog({
  opened,
  onClose,
  phase,
  documentContent,
  onApprove,
  loading = false,
}: ApprovalDialogProps) {
  const [feedback, setFeedback] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async (approved: boolean) => {
    if (!approved && !feedback.trim()) {
      setError('Feedback is required when requesting changes');
      return;
    }

    setError(null);
    
    try {
      await onApprove(approved, feedback.trim() || undefined);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process approval');
    }
  };

  const handleClose = () => {
    setFeedback('');
    setError(null);
    onClose();
  };

  const getPhaseTitle = () => {
    switch (phase) {
      case WorkflowPhase.REQUIREMENTS:
        return 'Requirements Document';
      case WorkflowPhase.DESIGN:
        return 'Design Document';
      case WorkflowPhase.TASKS:
        return 'Implementation Tasks';
      default:
        return 'Document';
    }
  };

  const getPhaseColor = () => {
    switch (phase) {
      case WorkflowPhase.REQUIREMENTS:
        return 'blue';
      case WorkflowPhase.DESIGN:
        return 'orange';
      case WorkflowPhase.TASKS:
        return 'green';
      default:
        return 'gray';
    }
  };

  const getPhaseDescription = () => {
    switch (phase) {
      case WorkflowPhase.REQUIREMENTS:
        return 'Review the requirements document to ensure it captures all necessary functionality, edge cases, and acceptance criteria.';
      case WorkflowPhase.DESIGN:
        return 'Review the design document to verify the technical approach, architecture decisions, and implementation strategy.';
      case WorkflowPhase.TASKS:
        return 'Review the implementation tasks to confirm they are actionable, properly sequenced, and cover all requirements.';
      default:
        return 'Review the document content and provide your approval or feedback.';
    }
  };

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={
        <Group gap="sm">
          <Title order={3}>Approve {getPhaseTitle()}</Title>
          <Badge color={getPhaseColor()} variant="light">
            {phase.charAt(0).toUpperCase() + phase.slice(1)} Phase
          </Badge>
        </Group>
      }
      size="xl"
      centered
    >
      <Stack gap="md">
        <Text size="sm" c="dimmed">
          {getPhaseDescription()}
        </Text>

        <Divider />

        <Stack gap="xs">
          <Text fw={500}>Document Content Preview</Text>
          <ScrollArea style={{ height: '300px' }}>
            <div
              style={{
                border: '1px solid var(--mantine-color-gray-3)',
                borderRadius: '8px',
                padding: '16px',
                backgroundColor: 'var(--mantine-color-gray-0)',
                fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                fontSize: '12px',
                whiteSpace: 'pre-wrap',
                overflow: 'auto',
              }}
            >
              {documentContent || (
                <Text c="dimmed" ta="center" mt="xl">
                  No content available for preview.
                </Text>
              )}
            </div>
          </ScrollArea>
        </Stack>

        <Divider />

        <Stack gap="sm">
          <Text fw={500}>Feedback (Optional for approval, required for changes)</Text>
          <Textarea
            placeholder={`Provide feedback about the ${phase} document...`}
            value={feedback}
            onChange={(event) => setFeedback(event.currentTarget.value)}
            minRows={4}
            maxRows={8}
            description="Your feedback will help improve the document quality and guide any necessary revisions."
          />
        </Stack>

        {error && (
          <Alert icon={<IconAlertCircle size={16} />} color="red">
            {error}
          </Alert>
        )}

        <Group justify="space-between" mt="md">
          <Button variant="default" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          
          <Group gap="sm">
            <Button
              color="red"
              variant="light"
              leftSection={<IconX size={16} />}
              onClick={() => handleApprove(false)}
              loading={loading}
              disabled={!feedback.trim()}
            >
              Request Changes
            </Button>
            <Button
              color="teal"
              leftSection={<IconCheck size={16} />}
              onClick={() => handleApprove(true)}
              loading={loading}
            >
              Approve & Continue
            </Button>
          </Group>
        </Group>
      </Stack>
    </Modal>
  );
}