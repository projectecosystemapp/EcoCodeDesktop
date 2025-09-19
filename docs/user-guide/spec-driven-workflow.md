# Spec-Driven Workflow User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Creating Your First Spec](#creating-your-first-spec)
4. [Understanding the Workflow](#understanding-the-workflow)
5. [Working with Requirements](#working-with-requirements)
6. [Designing Your Feature](#designing-your-feature)
7. [Managing Implementation Tasks](#managing-implementation-tasks)
8. [Executing Tasks](#executing-tasks)
9. [Monitoring Progress](#monitoring-progress)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

## Introduction

The Spec-Driven Workflow is a systematic approach to software development that transforms rough feature ideas into production-ready implementations through a structured three-phase process:

1. **Requirements Phase** - Define what needs to be built
2. **Design Phase** - Plan how it will be built
3. **Tasks Phase** - Break down the implementation into actionable steps

This methodology ensures thorough planning, maintains implementation context, and provides clear progress tracking throughout the development lifecycle.

### Key Benefits

- **Systematic Approach**: Structured workflow prevents missed requirements and design considerations
- **AI-Assisted Generation**: Intelligent document generation with research integration
- **Traceability**: Full traceability from requirements through implementation
- **Progress Tracking**: Granular progress monitoring and status updates
- **Quality Assurance**: Built-in validation and approval workflows
- **Context Preservation**: Maintains full context for implementation decisions

## Getting Started

### Prerequisites

Before using the spec-driven workflow, ensure you have:

1. **EcoCode Desktop Application** installed and running
2. **Orchestrator Service** running on port 8890
3. **Project Workspace** initialized with encryption
4. **AWS Bedrock Access** (optional, for AI-assisted generation)

### Accessing the Workflow

1. Open the EcoCode desktop application
2. Navigate to the **Spec Workflows** tab
3. Ensure the orchestrator service is healthy (green status indicator)

## Creating Your First Spec

### Step 1: Initiate Spec Creation

1. Click the **"Create New Spec"** button
2. Enter your feature idea in natural language
3. Optionally provide a custom feature name (kebab-case format)
4. Click **"Create Spec"**

**Example Feature Ideas:**
- "User authentication system with OAuth integration"
- "Real-time chat functionality with message history"
- "File upload system with virus scanning"
- "API rate limiting with Redis backend"

### Step 2: Review Generated Spec Structure

The system will automatically:
- Generate a unique spec ID
- Create the directory structure in `.kiro/specs/{feature-name}/`
- Initialize the workflow in the Requirements phase
- Generate an initial requirements document

## Understanding the Workflow

### Workflow Phases

The spec-driven workflow follows a strict sequential process:

```
Requirements → Design → Tasks → Execution
     ↓           ↓        ↓        ↓
   Review    Research   Plan    Implement
```

### Phase Transitions

- **Explicit Approval Required**: Each phase must be explicitly approved before proceeding
- **Iterative Refinement**: You can request changes and iterate within each phase
- **Backward Navigation**: You can return to previous phases if needed
- **Context Preservation**: All decisions and rationale are preserved

### Status Indicators

- 🟡 **Draft** - Initial creation, not yet reviewed
- 🔵 **In Review** - Under review, awaiting approval
- 🟢 **Approved** - Approved and ready for next phase
- 🟠 **In Progress** - Active implementation
- ✅ **Completed** - All tasks finished
- 🔴 **Error** - Requires attention

## Working with Requirements

### Requirements Document Structure

The requirements document follows the EARS (Easy Approach to Requirements Syntax) format:

```markdown
# Requirements Document

## Introduction
[High-level feature description and business context]

## Requirements

### Requirement 1: [Requirement Name]

**User Story:** As a [role], I want [feature], so that [benefit]

#### Acceptance Criteria
1. WHEN [event] THEN [system] SHALL [response]
2. IF [condition] THEN [system] SHALL [response]
3. GIVEN [precondition] WHEN [event] THEN [system] SHALL [response]
```

### Best Practices for Requirements

1. **Be Specific**: Use concrete, measurable criteria
2. **Consider Edge Cases**: Include error conditions and boundary cases
3. **Think Security**: Address authentication, authorization, and data protection
4. **Performance Matters**: Include performance and scalability requirements
5. **User Experience**: Consider usability and accessibility requirements

### Example Requirements

```markdown
### Requirement 1: User Authentication

**User Story:** As a user, I want to log in securely, so that I can access my personal data

#### Acceptance Criteria
1. WHEN a user enters valid credentials THEN the system SHALL authenticate and redirect to dashboard
2. WHEN a user enters invalid credentials THEN the system SHALL display an error message and log the attempt
3. IF a user fails authentication 5 times THEN the system SHALL temporarily lock the account for 15 minutes
4. WHEN a user is authenticated THEN the system SHALL create a secure session token with 24-hour expiration
```

### Reviewing and Approving Requirements

1. **Review Generated Content**: Carefully read the AI-generated requirements
2. **Request Changes**: Use the feedback feature to request modifications
3. **Iterate as Needed**: Continue refining until requirements are complete
4. **Explicit Approval**: Click "Approve Requirements" to proceed to design

## Designing Your Feature

### Design Document Structure

The design document includes comprehensive technical specifications:

- **Overview**: High-level architecture summary
- **Architecture**: System boundaries, data flow, technology stack
- **Components and Interfaces**: API definitions and interactions
- **Data Models**: Schemas, relationships, validation rules
- **Error Handling**: Error scenarios and recovery strategies
- **Testing Strategy**: Unit, integration, and end-to-end testing plans

### Research Integration

During design creation, the system automatically:
- Identifies research areas from requirements
- Gathers relevant technical information
- Incorporates findings into design decisions
- Provides source citations and references

### Design Review Process

1. **Automatic Generation**: AI creates initial design based on requirements
2. **Research Integration**: System conducts research and incorporates findings
3. **Review and Feedback**: Provide feedback on design decisions
4. **Iterative Refinement**: Modify design based on feedback
5. **Final Approval**: Approve design to proceed to task creation

## Managing Implementation Tasks

### Task List Structure

The task list breaks down implementation into manageable coding steps:

```markdown
# Implementation Plan

- [ ] 1. Set up project structure and core interfaces
  - Create directory structure for models, services, repositories
  - Define interfaces that establish system boundaries
  - _Requirements: 1.1, 1.2_

- [ ] 2. Implement data models and validation
- [ ] 2.1 Create core data model interfaces and types
  - Write TypeScript interfaces for all data models
  - Implement validation functions for data integrity
  - _Requirements: 2.1, 3.3_
```

### Task Characteristics

- **Coding-Focused**: Only includes tasks that involve writing, modifying, or testing code
- **Incremental**: Each task builds on previous tasks
- **Traceable**: Every task references specific requirements
- **Testable**: Includes validation and testing steps
- **Actionable**: Specific enough for autonomous execution

### Task Review and Approval

1. **Generated Task List**: Review AI-generated implementation plan
2. **Sequence Validation**: Ensure logical task ordering
3. **Requirement Coverage**: Verify all requirements are addressed
4. **Feedback and Iteration**: Request changes if needed
5. **Final Approval**: Approve tasks to begin execution

## Executing Tasks

### Task Execution Process

1. **Select Task**: Choose the next task to execute
2. **Context Loading**: System loads requirements, design, and task context
3. **Implementation**: AI agent implements the task with full context
4. **Validation**: Implementation is validated against requirements
5. **Status Update**: Task status is updated to completed
6. **Progress Tracking**: Overall progress is updated

### Task Execution Rules

- **One Task at a Time**: Execute tasks individually for better control
- **Sequential Order**: Follow the planned sequence for dependencies
- **Sub-task Priority**: Complete all sub-tasks before parent task
- **Context Awareness**: Full specification context is always available
- **Validation Required**: Each task must pass validation checks

### Monitoring Task Execution

- **Real-time Logs**: View execution logs as tasks run
- **Status Updates**: Track task status changes
- **Progress Indicators**: Monitor overall completion percentage
- **Error Handling**: Automatic error detection and recovery

## Monitoring Progress

### Progress Dashboard

The progress dashboard provides comprehensive tracking:

- **Overall Progress**: Percentage completion across all tasks
- **Phase Status**: Current workflow phase and approval status
- **Task Breakdown**: Detailed task status (not started, in progress, completed, blocked)
- **Recent Activity**: Timeline of recent changes and updates
- **Performance Metrics**: Execution times and success rates

### Progress Indicators

- **Completion Percentage**: Based on task completion and weighting
- **Phase Progress**: Visual indicators for each workflow phase
- **Task Status Colors**:
  - ⚪ Not Started
  - 🟡 In Progress
  - 🟢 Completed
  - 🔴 Blocked/Error

### Notifications and Alerts

- **Phase Completion**: Notifications when phases are completed
- **Approval Required**: Alerts when approval is needed
- **Task Completion**: Updates when tasks finish
- **Error Notifications**: Alerts for execution errors or blocks

## Best Practices

### 1. Feature Scoping

- **Start Small**: Begin with well-defined, focused features
- **Clear Boundaries**: Define what's included and excluded
- **Incremental Development**: Plan for iterative delivery
- **User-Centric**: Focus on user value and experience

### 2. Requirements Quality

- **Specific and Measurable**: Use concrete acceptance criteria
- **Complete Coverage**: Address all functional and non-functional requirements
- **Edge Case Consideration**: Include error conditions and boundary cases
- **Stakeholder Review**: Involve relevant stakeholders in requirements review

### 3. Design Excellence

- **Architecture First**: Establish clear architectural boundaries
- **Technology Alignment**: Choose technologies that fit the ecosystem
- **Scalability Planning**: Consider future growth and performance needs
- **Security by Design**: Integrate security considerations throughout

### 4. Task Management

- **Logical Sequencing**: Ensure tasks build incrementally
- **Appropriate Granularity**: Tasks should be neither too large nor too small
- **Clear Dependencies**: Identify and document task dependencies
- **Testability**: Include testing and validation in task planning

### 5. Execution Discipline

- **Follow the Process**: Stick to the sequential workflow
- **One Task Focus**: Complete tasks individually before moving on
- **Context Awareness**: Always maintain full specification context
- **Quality Gates**: Validate each task against requirements

## Troubleshooting

### Common Issues and Solutions

#### 1. Spec Creation Fails

**Symptoms**: Error during spec creation, incomplete directory structure

**Solutions**:
- Check orchestrator service health
- Verify workspace permissions
- Ensure sufficient disk space
- Review error logs for specific issues

#### 2. Requirements Generation Issues

**Symptoms**: Poor quality requirements, missing sections

**Solutions**:
- Provide more detailed feature ideas
- Use specific, actionable language
- Include business context and user roles
- Iterate with feedback to improve quality

#### 3. Design Research Problems

**Symptoms**: Limited research findings, outdated information

**Solutions**:
- Check internet connectivity
- Verify AWS Bedrock access (if enabled)
- Provide more specific technical context
- Manually supplement research findings

#### 4. Task Execution Failures

**Symptoms**: Tasks fail to execute, incomplete implementations

**Solutions**:
- Verify all prerequisite documents exist
- Check task dependencies are met
- Review execution logs for errors
- Ensure proper development environment setup

#### 5. Approval Workflow Issues

**Symptoms**: Cannot approve phases, stuck in review

**Solutions**:
- Provide explicit approval responses ("yes", "approved")
- Address all feedback before re-requesting approval
- Check for validation errors in documents
- Review workflow status indicators

### Getting Help

#### Log Files

Check these log locations for debugging:

- **Desktop Application**: Developer tools console
- **Orchestrator Service**: `/var/log/ecocode/orchestrator.log` (production)
- **Task Execution**: Execution logs in the UI

#### Health Checks

Use the health check endpoints:

```bash
# Basic health
curl http://localhost:8890/health

# Detailed health with system info
curl http://localhost:8890/health/detailed
```

#### Support Resources

- **API Documentation**: `/docs/api/specs-api.md`
- **Configuration Guide**: `/docs/setup/local.md`
- **Architecture Overview**: `/docs/specs/designs/README.md`

### Performance Optimization

#### For Large Specs

- Enable file and AI caching
- Use appropriate task granularity
- Monitor system resources
- Consider breaking large features into smaller specs

#### For Multiple Specs

- Limit concurrent spec execution
- Use progress monitoring to track resource usage
- Implement proper cleanup procedures
- Monitor disk space usage

### Security Considerations

- **Sensitive Data**: Avoid including sensitive information in specs
- **Access Control**: Ensure proper workspace permissions
- **Encryption**: Verify workspace encryption is enabled
- **Audit Trail**: Maintain logs for compliance and debugging

## Advanced Usage

### Custom Templates

You can customize document templates by modifying the generator configurations:

- Requirements templates in `eco_api/specs/generators.py`
- Design section templates in configuration
- Task format customization through settings

### Integration with CI/CD

The spec-driven workflow can integrate with CI/CD pipelines:

- Use webhooks for automated notifications
- Trigger builds on task completion
- Integrate with project management tools
- Export progress reports for stakeholders

### Batch Operations

For managing multiple specs:

- Use the API for bulk operations
- Implement custom scripts for repetitive tasks
- Monitor progress across multiple specs
- Generate consolidated reports

This user guide provides comprehensive coverage of the spec-driven workflow. For additional technical details, refer to the API documentation and architecture guides.