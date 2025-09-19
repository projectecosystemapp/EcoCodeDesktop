import { useEffect, useState } from 'react';
import {
  Notification,
  Stack,
  Group,
  Text,
  Badge,
  ActionIcon,
  Tooltip,
} from '@mantine/core';
import {
  IconCheck,
  IconX,
  IconClock,
  IconAlertCircle,
  IconBell,
  IconBellOff,
} from '@tabler/icons-react';
import { WorkflowPhase } from '../../shared/types';

interface ApprovalNotification {
  id: string;
  specId: string;
  specName: string;
  phase: WorkflowPhase;
  type: 'approved' | 'rejected' | 'pending' | 'ready_for_review';
  message: string;
  timestamp: Date;
  feedback?: string;
}

interface ApprovalNotificationsProps {
  notifications: ApprovalNotification[];
  onDismiss: (notificationId: string) => void;
  onClearAll: () => void;
  maxVisible?: number;
}

export function ApprovalNotifications({
  notifications,
  onDismiss,
  onClearAll,
  maxVisible = 5,
}: ApprovalNotificationsProps) {
  const [visible, setVisible] = useState(true);

  const getNotificationColor = (type: ApprovalNotification['type']) => {
    switch (type) {
      case 'approved':
        return 'teal';
      case 'rejected':
        return 'red';
      case 'pending':
        return 'yellow';
      case 'ready_for_review':
        return 'blue';
      default:
        return 'gray';
    }
  };

  const getNotificationIcon = (type: ApprovalNotification['type']) => {
    switch (type) {
      case 'approved':
        return <IconCheck size={16} />;
      case 'rejected':
        return <IconX size={16} />;
      case 'pending':
        return <IconClock size={16} />;
      case 'ready_for_review':
        return <IconAlertCircle size={16} />;
      default:
        return <IconBell size={16} />;
    }
  };

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

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - timestamp.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return timestamp.toLocaleDateString();
  };

  const visibleNotifications = notifications.slice(0, maxVisible);

  if (!visible || notifications.length === 0) {
    return null;
  }

  return (
    <Stack
      gap="xs"
      style={{
        position: 'fixed',
        top: '80px',
        right: '20px',
        zIndex: 1000,
        maxWidth: '400px',
      }}
    >
      <Group justify="space-between" align="center" mb="xs">
        <Group gap="xs">
          <IconBell size={16} />
          <Text size="sm" fw={500}>
            Approval Notifications ({notifications.length})
          </Text>
        </Group>
        <Group gap="xs">
          {notifications.length > maxVisible && (
            <Text size="xs" c="dimmed">
              +{notifications.length - maxVisible} more
            </Text>
          )}
          <Tooltip label="Hide notifications">
            <ActionIcon
              size="sm"
              variant="subtle"
              onClick={() => setVisible(false)}
            >
              <IconBellOff size={14} />
            </ActionIcon>
          </Tooltip>
          <Tooltip label="Clear all">
            <ActionIcon
              size="sm"
              variant="subtle"
              color="red"
              onClick={onClearAll}
            >
              <IconX size={14} />
            </ActionIcon>
          </Tooltip>
        </Group>
      </Group>

      {visibleNotifications.map((notification) => (
        <Notification
          key={notification.id}
          icon={getNotificationIcon(notification.type)}
          color={getNotificationColor(notification.type)}
          title={
            <Group gap="xs" align="center">
              <Text size="sm" fw={500}>
                {notification.specName}
              </Text>
              <Badge
                color={getPhaseColor(notification.phase)}
                variant="light"
                size="xs"
              >
                {notification.phase.charAt(0).toUpperCase() + notification.phase.slice(1)}
              </Badge>
            </Group>
          }
          onClose={() => onDismiss(notification.id)}
          style={{ maxWidth: '100%' }}
        >
          <Stack gap="xs">
            <Text size="sm">{notification.message}</Text>
            
            {notification.feedback && (
              <Text size="xs" c="dimmed" style={{ fontStyle: 'italic' }}>
                "{notification.feedback}"
              </Text>
            )}
            
            <Text size="xs" c="dimmed">
              {formatTimestamp(notification.timestamp)}
            </Text>
          </Stack>
        </Notification>
      ))}
    </Stack>
  );
}

// Hook for managing approval notifications
export function useApprovalNotifications() {
  const [notifications, setNotifications] = useState<ApprovalNotification[]>([]);

  const addNotification = (notification: Omit<ApprovalNotification, 'id' | 'timestamp'>) => {
    const newNotification: ApprovalNotification = {
      ...notification,
      id: `${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
    };
    
    setNotifications((prev) => [newNotification, ...prev]);
  };

  const dismissNotification = (notificationId: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== notificationId));
  };

  const clearAllNotifications = () => {
    setNotifications([]);
  };

  const addApprovalNotification = (
    specId: string,
    specName: string,
    phase: WorkflowPhase,
    approved: boolean,
    feedback?: string
  ) => {
    addNotification({
      specId,
      specName,
      phase,
      type: approved ? 'approved' : 'rejected',
      message: approved 
        ? `${phase.charAt(0).toUpperCase() + phase.slice(1)} phase approved successfully`
        : `${phase.charAt(0).toUpperCase() + phase.slice(1)} phase requires changes`,
      feedback,
    });
  };

  const addReadyForReviewNotification = (
    specId: string,
    specName: string,
    phase: WorkflowPhase
  ) => {
    addNotification({
      specId,
      specName,
      phase,
      type: 'ready_for_review',
      message: `${phase.charAt(0).toUpperCase() + phase.slice(1)} document is ready for review`,
    });
  };

  const addPendingNotification = (
    specId: string,
    specName: string,
    phase: WorkflowPhase,
    message: string
  ) => {
    addNotification({
      specId,
      specName,
      phase,
      type: 'pending',
      message,
    });
  };

  return {
    notifications,
    addNotification,
    dismissNotification,
    clearAllNotifications,
    addApprovalNotification,
    addReadyForReviewNotification,
    addPendingNotification,
  };
}