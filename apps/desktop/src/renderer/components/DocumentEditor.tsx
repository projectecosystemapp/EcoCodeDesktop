import { useState, useEffect } from 'react';
import {
  Button,
  Group,
  Stack,
  Textarea,
  Title,
  Alert,
  Badge,
  Text,
  Loader,
  ActionIcon,
  Tooltip,
} from '@mantine/core';
import { IconAlertCircle, IconCheck, IconEdit, IconEye, IconX } from '@tabler/icons-react';
import type { UpdateDocumentRequest, UpdateDocumentResponse } from '../../main/orchestrator-client';
import type { WorkflowPhase } from '../../shared/types';

interface DocumentEditorProps {
  specId: string;
  documentType: 'requirements' | 'design' | 'tasks';
  phase: WorkflowPhase;
  content: string;
  isApproved?: boolean;
  onUpdate: (content: string, approve?: boolean, feedback?: string) => Promise<UpdateDocumentResponse>;
  onApprove?: (approved: boolean, feedback?: string) => Promise<void>;
  readOnly?: boolean;
}

export function DocumentEditor({
  specId,
  documentType,
  phase,
  content,
  isApproved = false,
  onUpdate,
  onApprove,
  readOnly = false,
}: DocumentEditorProps) {
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState(content);
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    setEditContent(content);
  }, [content]);

  const handleSave = async () => {
    if (!editContent.trim()) {
      setError('Document content cannot be empty');
      return;
    }

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const request: UpdateDocumentRequest = {
        content: editContent.trim(),
      };

      const result = await onUpdate(editContent.trim());
      setSuccess(result.message);
      setEditMode(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update document');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (approved: boolean) => {
    if (!onApprove) return;

    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      await onApprove(approved, feedback.trim() || undefined);
      setSuccess(approved ? 'Document approved successfully' : 'Feedback submitted successfully');
      setFeedback('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process approval');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setEditContent(content);
    setEditMode(false);
    setError(null);
    setSuccess(null);
  };

  const getDocumentTitle = () => {
    switch (documentType) {
      case 'requirements':
        return 'Requirements Document';
      case 'design':
        return 'Design Document';
      case 'tasks':
        return 'Implementation Tasks';
      default:
        return 'Document';
    }
  };

  const getPhaseColor = () => {
    switch (phase) {
      case 'requirements':
        return 'blue';
      case 'design':
        return 'orange';
      case 'tasks':
        return 'green';
      case 'execution':
        return 'purple';
      default:
        return 'gray';
    }
  };

  return (
    <Stack gap="md">
      <Group justify="space-between" align="center">
        <Group gap="sm">
          <Title order={3}>{getDocumentTitle()}</Title>
          <Badge color={getPhaseColor()} variant="light">
            {phase.charAt(0).toUpperCase() + phase.slice(1)} Phase
          </Badge>
          {isApproved && (
            <Badge color="teal" leftSection={<IconCheck size={12} />}>
              Approved
            </Badge>
          )}
        </Group>
        
        {!readOnly && (
          <Group gap="xs">
            {!editMode ? (
              <Tooltip label="Edit document">
                <ActionIcon
                  variant="light"
                  color="blue"
                  onClick={() => setEditMode(true)}
                  disabled={loading}
                >
                  <IconEdit size={16} />
                </ActionIcon>
              </Tooltip>
            ) : (
              <Group gap="xs">
                <Tooltip label="Cancel editing">
                  <ActionIcon
                    variant="light"
                    color="gray"
                    onClick={handleCancel}
                    disabled={loading}
                  >
                    <IconX size={16} />
                  </ActionIcon>
                </Tooltip>
                <Button size="xs" onClick={handleSave} loading={loading}>
                  Save Changes
                </Button>
              </Group>
            )}
          </Group>
        )}
      </Group>

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

      <Stack gap="sm">
        {editMode ? (
          <Textarea
            value={editContent}
            onChange={(event) => setEditContent(event.currentTarget.value)}
            minRows={20}
            maxRows={30}
            placeholder={`Enter ${documentType} content in Markdown format...`}
            styles={{
              input: {
                fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                fontSize: '14px',
              },
            }}
          />
        ) : (
          <div
            style={{
              border: '1px solid var(--mantine-color-gray-3)',
              borderRadius: '8px',
              padding: '16px',
              minHeight: '400px',
              backgroundColor: 'var(--mantine-color-gray-0)',
              fontFamily: 'Monaco, Consolas, "Courier New", monospace',
              fontSize: '14px',
              whiteSpace: 'pre-wrap',
              overflow: 'auto',
            }}
          >
            {content || (
              <Text c="dimmed" ta="center" mt="xl">
                No content available. Click edit to add content.
              </Text>
            )}
          </div>
        )}
      </Stack>

      {onApprove && !isApproved && !editMode && content && (
        <Stack gap="md">
          <Textarea
            label="Feedback (Optional)"
            placeholder="Provide feedback or suggestions for improvements..."
            value={feedback}
            onChange={(event) => setFeedback(event.currentTarget.value)}
            minRows={3}
          />
          
          <Group gap="sm">
            <Button
              color="red"
              variant="light"
              onClick={() => handleApprove(false)}
              loading={loading}
              disabled={!feedback.trim()}
            >
              Request Changes
            </Button>
            <Button
              color="teal"
              onClick={() => handleApprove(true)}
              loading={loading}
            >
              Approve & Continue
            </Button>
          </Group>
        </Stack>
      )}
    </Stack>
  );
}