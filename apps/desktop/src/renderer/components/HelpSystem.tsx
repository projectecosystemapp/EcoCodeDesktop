import React, { useState } from 'react';
import {
  Modal,
  Button,
  Group,
  Stack,
  Text,
  Title,
  Tabs,
  List,
  Code,
  Alert,
  Anchor,
  ActionIcon,
  Tooltip,
  Badge,
} from '@mantine/core';
import {
  IconHelp,
  IconInfoCircle,
  IconBook,
  IconRocket,
  IconSettings,
  IconBulb,
  IconAlertTriangle,
} from '@tabler/icons-react';

interface HelpSystemProps {
  opened: boolean;
  onClose: () => void;
  context?: 'overview' | 'creation' | 'requirements' | 'design' | 'tasks' | 'execution';
}

export function HelpSystem({ opened, onClose, context = 'overview' }: HelpSystemProps) {
  const [activeTab, setActiveTab] = useState(context);

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={
        <Group gap="sm">
          <IconBook size={20} />
          <Title order={3}>Spec-Driven Workflow Help</Title>
        </Group>
      }
      size="xl"
      centered
    >
      <Tabs value={activeTab} onChange={(value) => setActiveTab(value || 'overview')}>
        <Tabs.List>
          <Tabs.Tab value="overview" leftSection={<IconInfoCircle size={16} />}>
            Overview
          </Tabs.Tab>
          <Tabs.Tab value="creation" leftSection={<IconRocket size={16} />}>
            Getting Started
          </Tabs.Tab>
          <Tabs.Tab value="requirements" leftSection={<IconBook size={16} />}>
            Requirements
          </Tabs.Tab>
          <Tabs.Tab value="design" leftSection={<IconSettings size={16} />}>
            Design
          </Tabs.Tab>
          <Tabs.Tab value="tasks" leftSection={<IconBulb size={16} />}>
            Tasks
          </Tabs.Tab>
          <Tabs.Tab value="execution" leftSection={<IconRocket size={16} />}>
            Execution
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="overview" pt="md">
          <Stack gap="md">
            <Alert icon={<IconInfoCircle size={16} />} title="What is Spec-Driven Development?">
              <Text size="sm">
                Spec-driven development is a systematic approach that transforms rough feature ideas 
                into production-ready implementations through a structured three-phase process.
              </Text>
            </Alert>

            <Title order={4}>The Three-Phase Workflow</Title>
            <List spacing="sm">
              <List.Item>
                <Group gap="xs">
                  <Badge color="blue" size="sm">1</Badge>
                  <Text fw={500}>Requirements</Text>
                  <Text size="sm" c="dimmed">Define what needs to be built</Text>
                </Group>
              </List.Item>
              <List.Item>
                <Group gap="xs">
                  <Badge color="green" size="sm">2</Badge>
                  <Text fw={500}>Design</Text>
                  <Text size="sm" c="dimmed">Plan how it will be built</Text>
                </Group>
              </List.Item>
              <List.Item>
                <Group gap="xs">
                  <Badge color="orange" size="sm">3</Badge>
                  <Text fw={500}>Tasks</Text>
                  <Text size="sm" c="dimmed">Break down into actionable steps</Text>
                </Group>
              </List.Item>
            </List>

            <Title order={4}>Key Benefits</Title>
            <List spacing="xs" size="sm">
              <List.Item>Systematic approach prevents missed requirements</List.Item>
              <List.Item>AI-assisted generation with research integration</List.Item>
              <List.Item>Full traceability from requirements to implementation</List.Item>
              <List.Item>Granular progress monitoring and status updates</List.Item>
              <List.Item>Built-in validation and approval workflows</List.Item>
            </List>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="creation" pt="md">
          <Stack gap="md">
            <Title order={4}>Creating Your First Spec</Title>
            
            <Alert icon={<IconRocket size={16} />} title="Quick Start">
              <Text size="sm">
                Follow these steps to create your first specification and start the workflow.
              </Text>
            </Alert>

            <List spacing="md" type="ordered">
              <List.Item>
                <Stack gap="xs">
                  <Text fw={500}>Click "Create New Spec"</Text>
                  <Text size="sm" c="dimmed">
                    Start by clicking the create button in the spec workflow interface.
                  </Text>
                </Stack>
              </List.Item>
              
              <List.Item>
                <Stack gap="xs">
                  <Text fw={500}>Describe Your Feature Idea</Text>
                  <Text size="sm" c="dimmed">
                    Enter a clear description of what you want to build. Be specific about the functionality.
                  </Text>
                  <Code block>
                    Example: "User authentication system with OAuth integration and password reset functionality"
                  </Code>
                </Stack>
              </List.Item>
              
              <List.Item>
                <Stack gap="xs">
                  <Text fw={500}>Review Generated Structure</Text>
                  <Text size="sm" c="dimmed">
                    The system will create a unique spec ID and initialize the workflow in the Requirements phase.
                  </Text>
                </Stack>
              </List.Item>
            </List>

            <Alert icon={<IconBulb size={16} />} title="Pro Tips">
              <List size="sm" spacing="xs">
                <List.Item>Use clear, specific language in your feature descriptions</List.Item>
                <List.Item>Include business context and user benefits</List.Item>
                <List.Item>Start with smaller, focused features for your first specs</List.Item>
                <List.Item>Consider the target users and their needs</List.Item>
              </List>
            </Alert>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="requirements" pt="md">
          <Stack gap="md">
            <Title order={4}>Working with Requirements</Title>
            
            <Alert icon={<IconBook size={16} />} title="EARS Format">
              <Text size="sm">
                Requirements use the EARS (Easy Approach to Requirements Syntax) format for clarity and precision.
              </Text>
            </Alert>

            <Title order={5}>Requirements Structure</Title>
            <Code block>
{`### Requirement 1: [Name]

**User Story:** As a [role], I want [feature], so that [benefit]

#### Acceptance Criteria
1. WHEN [event] THEN [system] SHALL [response]
2. IF [condition] THEN [system] SHALL [response]
3. GIVEN [precondition] WHEN [event] THEN [system] SHALL [response]`}
            </Code>

            <Title order={5}>Best Practices</Title>
            <List spacing="xs" size="sm">
              <List.Item><Text fw={500}>Be Specific:</Text> Use concrete, measurable criteria</List.Item>
              <List.Item><Text fw={500}>Consider Edge Cases:</Text> Include error conditions and boundary cases</List.Item>
              <List.Item><Text fw={500}>Think Security:</Text> Address authentication and data protection</List.Item>
              <List.Item><Text fw={500}>Performance Matters:</Text> Include scalability requirements</List.Item>
              <List.Item><Text fw={500}>User Experience:</Text> Consider usability and accessibility</List.Item>
            </List>

            <Alert icon={<IconAlertTriangle size={16} />} title="Review Process">
              <Text size="sm">
                Carefully review AI-generated requirements. Use the feedback feature to request changes 
                and iterate until requirements are complete. Explicit approval is required to proceed.
              </Text>
            </Alert>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="design" pt="md">
          <Stack gap="md">
            <Title order={4}>Design Phase</Title>
            
            <Alert icon={<IconSettings size={16} />} title="Research Integration">
              <Text size="sm">
                The system automatically conducts research during design creation and incorporates 
                findings into technical specifications.
              </Text>
            </Alert>

            <Title order={5}>Design Document Sections</Title>
            <List spacing="sm">
              <List.Item><Text fw={500}>Overview:</Text> High-level architecture summary</List.Item>
              <List.Item><Text fw={500}>Architecture:</Text> System boundaries, data flow, technology stack</List.Item>
              <List.Item><Text fw={500}>Components:</Text> API definitions and interactions</List.Item>
              <List.Item><Text fw={500}>Data Models:</Text> Schemas, relationships, validation rules</List.Item>
              <List.Item><Text fw={500}>Error Handling:</Text> Error scenarios and recovery strategies</List.Item>
              <List.Item><Text fw={500}>Testing Strategy:</Text> Unit, integration, and end-to-end testing plans</List.Item>
            </List>

            <Title order={5}>Research Areas</Title>
            <Text size="sm" c="dimmed">
              The system automatically identifies and researches:
            </Text>
            <List spacing="xs" size="sm">
              <List.Item>Technology choices and frameworks</List.Item>
              <List.Item>Architectural patterns and best practices</List.Item>
              <List.Item>Integration points and APIs</List.Item>
              <List.Item>Performance and scalability considerations</List.Item>
              <List.Item>Security implications and requirements</List.Item>
            </List>

            <Alert icon={<IconBulb size={16} />} title="Design Review">
              <Text size="sm">
                Review the generated design carefully. The system provides rationale for design decisions 
                based on research findings. Request changes if needed before approval.
              </Text>
            </Alert>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="tasks" pt="md">
          <Stack gap="md">
            <Title order={4}>Implementation Tasks</Title>
            
            <Alert icon={<IconBulb size={16} />} title="Task Characteristics">
              <Text size="sm">
                Tasks are coding-focused, incremental, traceable, and actionable. Each task builds 
                on previous tasks and references specific requirements.
              </Text>
            </Alert>

            <Title order={5}>Task Structure</Title>
            <Code block>
{`- [ ] 1. Set up project structure
  - Create directory structure for models, services
  - Define interfaces that establish system boundaries
  - _Requirements: 1.1, 1.2_

- [ ] 2. Implement data models
- [ ] 2.1 Create core data model interfaces
  - Write TypeScript interfaces for all data models
  - Implement validation functions
  - _Requirements: 2.1, 3.3_`}
            </Code>

            <Title order={5}>Task Guidelines</Title>
            <List spacing="xs" size="sm">
              <List.Item><Text fw={500}>Coding Only:</Text> Tasks focus exclusively on writing, modifying, or testing code</List.Item>
              <List.Item><Text fw={500}>Incremental:</Text> Each task builds on previous tasks</List.Item>
              <List.Item><Text fw={500}>Traceable:</Text> Every task references specific requirements</List.Item>
              <List.Item><Text fw={500}>Testable:</Text> Includes validation and testing steps</List.Item>
              <List.Item><Text fw={500}>Actionable:</Text> Specific enough for autonomous execution</List.Item>
            </List>

            <Alert icon={<IconAlertTriangle size={16} />} title="Task Review">
              <Text size="sm">
                Review the generated task list for logical sequencing and requirement coverage. 
                Ensure all requirements are addressed before approving the task list.
              </Text>
            </Alert>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="execution" pt="md">
          <Stack gap="md">
            <Title order={4}>Task Execution</Title>
            
            <Alert icon={<IconRocket size={16} />} title="Execution Process">
              <Text size="sm">
                Tasks are executed with full context awareness, including requirements, design, 
                and implementation history.
              </Text>
            </Alert>

            <Title order={5}>Execution Rules</Title>
            <List spacing="sm">
              <List.Item><Text fw={500}>One Task at a Time:</Text> Execute tasks individually for better control</List.Item>
              <List.Item><Text fw={500}>Sequential Order:</Text> Follow the planned sequence for dependencies</List.Item>
              <List.Item><Text fw={500}>Sub-task Priority:</Text> Complete all sub-tasks before parent task</List.Item>
              <List.Item><Text fw={500}>Context Awareness:</Text> Full specification context is always available</List.Item>
              <List.Item><Text fw={500}>Validation Required:</Text> Each task must pass validation checks</List.Item>
            </List>

            <Title order={5}>Monitoring Execution</Title>
            <List spacing="xs" size="sm">
              <List.Item>View real-time execution logs as tasks run</List.Item>
              <List.Item>Track task status changes and progress updates</List.Item>
              <List.Item>Monitor overall completion percentage</List.Item>
              <List.Item>Automatic error detection and recovery</List.Item>
            </List>

            <Alert icon={<IconBulb size={16} />} title="Best Practice">
              <Text size="sm">
                Let each task complete fully before starting the next one. This ensures proper 
                dependency handling and maintains implementation quality.
              </Text>
            </Alert>
          </Stack>
        </Tabs.Panel>
      </Tabs>

      <Group justify="flex-end" mt="md">
        <Button onClick={onClose}>Close</Button>
        <Button 
          variant="light" 
          leftSection={<IconBook size={16} />}
          onClick={() => window.ecocode?.openExternal?.('https://docs.ecocode.dev/spec-workflow')}
        >
          Full Documentation
        </Button>
      </Group>
    </Modal>
  );
}

interface HelpButtonProps {
  context?: 'overview' | 'creation' | 'requirements' | 'design' | 'tasks' | 'execution';
  size?: 'sm' | 'md' | 'lg';
}

export function HelpButton({ context = 'overview', size = 'md' }: HelpButtonProps) {
  const [helpOpened, setHelpOpened] = useState(false);

  return (
    <>
      <Tooltip label="Get Help">
        <ActionIcon
          variant="subtle"
          color="blue"
          size={size}
          onClick={() => setHelpOpened(true)}
        >
          <IconHelp size={size === 'sm' ? 16 : size === 'lg' ? 24 : 20} />
        </ActionIcon>
      </Tooltip>
      
      <HelpSystem
        opened={helpOpened}
        onClose={() => setHelpOpened(false)}
        context={context}
      />
    </>
  );
}

interface ContextualHelpProps {
  title: string;
  children: React.ReactNode;
  type?: 'info' | 'tip' | 'warning';
}

export function ContextualHelp({ title, children, type = 'info' }: ContextualHelpProps) {
  const getIcon = () => {
    switch (type) {
      case 'tip':
        return <IconBulb size={16} />;
      case 'warning':
        return <IconAlertTriangle size={16} />;
      default:
        return <IconInfoCircle size={16} />;
    }
  };

  const getColor = () => {
    switch (type) {
      case 'tip':
        return 'yellow';
      case 'warning':
        return 'orange';
      default:
        return 'blue';
    }
  };

  return (
    <Alert icon={getIcon()} title={title} color={getColor()} variant="light">
      {children}
    </Alert>
  );
}

interface QuickTipProps {
  tip: string;
  visible?: boolean;
}

export function QuickTip({ tip, visible = true }: QuickTipProps) {
  if (!visible) return null;

  return (
    <Alert icon={<IconBulb size={16} />} color="yellow" variant="light" size="sm">
      <Text size="sm">{tip}</Text>
    </Alert>
  );
}