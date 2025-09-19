import { useState, useEffect } from 'react';
import {
  AppShell,
  Group,
  Title,
  Text,
  Badge,
  ActionIcon,
  Tooltip,
  Alert,
} from '@mantine/core';
import { IconRefresh, IconAlertCircle } from '@tabler/icons-react';
import { useSpecStore } from '../stores/specStore';
import { getLoadingCompat, getErrorMessage } from '../../shared/storeCompat';
import { useApprovalNotifications } from './ApprovalNotifications';
import {
  SpecList,
  SpecDetails,
  SpecCreationWizard,
  ApprovalDialog,
  ApprovalNotifications,
} from './index';
import { WorkflowPhase } from '../../shared/types';

export function SpecWorkflow() {
  const {
    specs,
    selectedSpec,
    loading: loadingState,
    error: errorState,
    loadSpecs,
    createSpec,
    selectSpec,
    refreshSelectedSpec,
    updateRequirements,
    updateDesign,
    updateTasks,
    approvePhase,
    executeTask,
    updateTaskStatus,
    clearError,
  } = useSpecStore();
  
  const loading = getLoadingCompat(loadingState);
  const error = getErrorMessage(errorState);

  const {
    notifications,
    dismissNotification,
    clearAllNotifications,
    addApprovalNotification,
    addReadyForReviewNotification,
  } = useApprovalNotifications();

  const [showCreateWizard, setShowCreateWizard] = useState(false);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalPhase, setApprovalPhase] = useState<WorkflowPhase>(WorkflowPhase.REQUIREMENTS);
  const [approvalContent, setApprovalContent] = useState('');

  useEffect(() => {
    loadSpecs();
  }, [loadSpecs]);

  const handleCreateSpec = async (specId: string) => {
    await selectSpec(specId);
    addReadyForReviewNotification(
      specId,
      selectedSpec?.featureName || 'New Spec',
      WorkflowPhase.REQUIREMENTS
    );
  };

  const handleSelectSpec = async (specId: string) => {
    await selectSpec(specId);
  };

  const handleRefresh = async () => {
    await loadSpecs();
    if (selectedSpec) {
      await refreshSelectedSpec();
    }
  };

  const handleUpdateDocument = async (
    documentType: 'requirements' | 'design' | 'tasks',
    content: string
  ) => {
    if (!selectedSpec) return;

    switch (documentType) {
      case 'requirements':
        await updateRequirements(selectedSpec.id, content);
        break;
      case 'design':
        await updateDesign(selectedSpec.id, content);
        break;
      case 'tasks':
        await updateTasks(selectedSpec.id, content);
        break;
    }
  };

  const handleApprovePhase = async (phase: string, approved: boolean, feedback?: string) => {
    if (!selectedSpec) return;

    await approvePhase(selectedSpec.id, phase, approved, feedback);
    
    addApprovalNotification(
      selectedSpec.id,
      selectedSpec.featureName,
      phase as WorkflowPhase,
      approved,
      feedback
    );
  };

  const handleExecuteTask = async (taskId: string) => {
    if (!selectedSpec) return;
    await executeTask(selectedSpec.id, taskId);
  };

  const handleUpdateTaskStatus = async (taskId: string, status: string) => {
    if (!selectedSpec) return;
    await updateTaskStatus(selectedSpec.id, taskId, status);
  };

  const openApprovalDialog = (phase: WorkflowPhase, content: string) => {
    setApprovalPhase(phase);
    setApprovalContent(content);
    setShowApprovalDialog(true);
  };

  return (
    <>
      <AppShell
        padding="0"
        header={{ height: 64 }}
        navbar={{ width: 400, breakpoint: 'sm' }}
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
            <Group gap="sm">
              <Title order={3} c="white">
                Spec-Driven Workflow
              </Title>
              <Badge color="blue" variant="light">
                {specs.length} Specifications
              </Badge>
            </Group>
            <Tooltip label="Refresh all data">
              <ActionIcon
                variant="light"
                color="blue"
                onClick={handleRefresh}
                loading={loading}
              >
                <IconRefresh size={18} />
              </ActionIcon>
            </Tooltip>
          </Group>
        </AppShell.Header>

        <AppShell.Navbar p="md">
          <SpecList
            specs={specs}
            loading={loading}
            error={error}
            onRefresh={loadSpecs}
            onCreateNew={() => setShowCreateWizard(true)}
            onSelectSpec={handleSelectSpec}
            selectedSpecId={selectedSpec?.id}
          />
        </AppShell.Navbar>

        <AppShell.Main p="md">
          {error && (
            <Alert
              icon={<IconAlertCircle size={16} />}
              color="red"
              onClose={clearError}
              mb="md"
            >
              {error}
            </Alert>
          )}
          
          <SpecDetails
            spec={selectedSpec}
            loading={loading}
            error={null}
            onRefresh={refreshSelectedSpec}
            onUpdateDocument={handleUpdateDocument}
            onApprovePhase={handleApprovePhase}
            onExecuteTask={handleExecuteTask}
            onUpdateTaskStatus={handleUpdateTaskStatus}
          />
        </AppShell.Main>
      </AppShell>

      <SpecCreationWizard
        opened={showCreateWizard}
        onClose={() => setShowCreateWizard(false)}
        onSpecCreated={handleCreateSpec}
      />

      <ApprovalDialog
        opened={showApprovalDialog}
        onClose={() => setShowApprovalDialog(false)}
        phase={approvalPhase}
        documentContent={approvalContent}
        onApprove={async (approved, feedback) => {
          if (selectedSpec) {
            await handleApprovePhase(approvalPhase, approved, feedback);
          }
        }}
        loading={loading}
      />

      <ApprovalNotifications
        notifications={notifications}
        onDismiss={dismissNotification}
        onClearAll={clearAllNotifications}
      />
    </>
  );
}