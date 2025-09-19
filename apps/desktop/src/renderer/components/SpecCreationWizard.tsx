import { useState } from 'react';
import {
  Button,
  Group,
  Modal,
  Stack,
  Stepper,
  Text,
  Textarea,
  TextInput,
  Title,
  Alert,
  Loader,
} from '@mantine/core';
import { IconAlertCircle, IconCheck } from '@tabler/icons-react';
import type { CreateSpecRequest } from '../../main/orchestrator-client';

interface SpecCreationWizardProps {
  opened: boolean;
  onClose: () => void;
  onSpecCreated: (specId: string) => void;
}

export function SpecCreationWizard({ opened, onClose, onSpecCreated }: SpecCreationWizardProps) {
  const [active, setActive] = useState(0);
  const [featureIdea, setFeatureIdea] = useState('');
  const [featureName, setFeatureName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNext = () => {
    if (active === 0 && featureIdea.trim().length < 3) {
      setError('Feature idea must be at least 3 characters long');
      return;
    }
    setError(null);
    setActive((current) => current + 1);
  };

  const handleBack = () => {
    setError(null);
    setActive((current) => current - 1);
  };

  const handleCreate = async () => {
    if (!featureIdea.trim()) {
      setError('Feature idea is required');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const request: CreateSpecRequest = {
        feature_idea: featureIdea.trim(),
        feature_name: featureName.trim() || undefined,
      };

      const result = await window.ecocode.specs.create(request);
      onSpecCreated(result.id);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create spec');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setActive(0);
    setFeatureIdea('');
    setFeatureName('');
    setError(null);
    setLoading(false);
    onClose();
  };

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title={<Title order={3}>Create New Specification</Title>}
      size="lg"
      centered
    >
      <Stack gap="md">
        <Stepper active={active} onStepClick={setActive} allowNextStepsSelect={false}>
          <Stepper.Step label="Feature Idea" description="Describe your feature concept">
            <Stack gap="md" mt="md">
              <Text size="sm" c="dimmed">
                Provide a rough description of the feature you want to build. This will be used to generate
                detailed requirements, design, and implementation tasks.
              </Text>
              <Textarea
                label="Feature Idea"
                placeholder="e.g., A user authentication system with email/password login, JWT tokens, and role-based access control..."
                value={featureIdea}
                onChange={(event) => setFeatureIdea(event.currentTarget.value)}
                minRows={4}
                maxRows={8}
                required
                error={error && active === 0 ? error : undefined}
              />
            </Stack>
          </Stepper.Step>

          <Stepper.Step label="Configuration" description="Optional settings">
            <Stack gap="md" mt="md">
              <Text size="sm" c="dimmed">
                Optionally provide a custom feature name. If left blank, a name will be generated automatically
                from your feature idea.
              </Text>
              <TextInput
                label="Feature Name (Optional)"
                placeholder="e.g., user-authentication"
                value={featureName}
                onChange={(event) => setFeatureName(event.currentTarget.value)}
                description="Use kebab-case format (lowercase with hyphens)"
              />
            </Stack>
          </Stepper.Step>

          <Stepper.Step label="Review" description="Confirm and create">
            <Stack gap="md" mt="md">
              <Text size="sm" c="dimmed">
                Review your specification details before creating the workflow.
              </Text>
              <Stack gap="xs">
                <Text fw={500}>Feature Idea:</Text>
                <Text size="sm" style={{ whiteSpace: 'pre-wrap' }}>
                  {featureIdea}
                </Text>
              </Stack>
              {featureName && (
                <Stack gap="xs">
                  <Text fw={500}>Feature Name:</Text>
                  <Text size="sm">{featureName}</Text>
                </Stack>
              )}
            </Stack>
          </Stepper.Step>

          <Stepper.Completed>
            <Stack align="center" gap="md" mt="md">
              <IconCheck size={48} color="var(--mantine-color-teal-6)" />
              <Text ta="center">Specification created successfully!</Text>
            </Stack>
          </Stepper.Completed>
        </Stepper>

        {error && (
          <Alert icon={<IconAlertCircle size={16} />} color="red">
            {error}
          </Alert>
        )}

        <Group justify="space-between" mt="xl">
          <Button variant="default" onClick={active === 0 ? handleClose : handleBack} disabled={loading}>
            {active === 0 ? 'Cancel' : 'Back'}
          </Button>
          
          {active < 2 ? (
            <Button onClick={handleNext} disabled={loading}>
              Next
            </Button>
          ) : (
            <Button onClick={handleCreate} loading={loading} disabled={!featureIdea.trim()}>
              Create Specification
            </Button>
          )}
        </Group>
      </Stack>
    </Modal>
  );
}