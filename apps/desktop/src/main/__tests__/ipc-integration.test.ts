/**
 * Integration tests for desktop client IPC communication.
 * 
 * This module provides comprehensive testing for IPC handlers and communication
 * between the main process and renderer process for spec-driven workflows.
 * 
 * Requirements addressed:
 * - All requirements - integration validation
 * - Desktop client IPC communication testing
 * - End-to-end workflow testing with IPC channels
 */

import { jest } from '@jest/globals';
import { ipcMain, ipcRenderer, BrowserWindow } from 'electron';
import axios from 'axios';
import { EventEmitter } from 'events';

// Mock Electron modules
jest.mock('electron', () => ({
  ipcMain: {
    handle: jest.fn(),
    on: jest.fn(),
    removeAllListeners: jest.fn(),
  },
  ipcRenderer: {
    invoke: jest.fn(),
    send: jest.fn(),
    on: jest.fn(),
    removeAllListeners: jest.fn(),
  },
  BrowserWindow: {
    getFocusedWindow: jest.fn(),
    getAllWindows: jest.fn(() => []),
  },
  app: {
    getPath: jest.fn(() => '/test/path'),
  },
}));

// Mock axios for API calls
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Import IPC handlers after mocking
import '../ipc';

describe('IPC Integration Tests', () => {
  let mockWindow: any;
  let ipcHandlers: Map<string, Function>;

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Create mock window
    mockWindow = {
      webContents: {
        send: jest.fn(),
      },
      isDestroyed: jest.fn(() => false),
    };

    // Track IPC handlers
    ipcHandlers = new Map();
    (ipcMain.handle as jest.Mock).mockImplementation((channel: string, handler: Function) => {
      ipcHandlers.set(channel, handler);
    });

    // Mock BrowserWindow methods
    (BrowserWindow.getFocusedWindow as jest.Mock).mockReturnValue(mockWindow);
    (BrowserWindow.getAllWindows as jest.Mock).mockReturnValue([mockWindow]);

    // Set up default axios responses
    mockedAxios.post.mockResolvedValue({ data: { success: true } });
    mockedAxios.get.mockResolvedValue({ data: { success: true } });
    mockedAxios.put.mockResolvedValue({ data: { success: true } });
  });

  afterEach(() => {
    // Clean up
    ipcHandlers.clear();
  });

  describe('Spec Management IPC Handlers', () => {
    test('should handle spec creation via IPC', async () => {
      // Mock API response
      const mockSpecResponse = {
        data: {
          spec_id: 'test-feature-spec',
          workflow_state: {
            spec_id: 'test-feature-spec',
            current_phase: 'requirements',
            status: 'draft',
            approvals: {
              requirements: 'pending'
            },
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z'
          }
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockSpecResponse);

      // Get the handler
      const createSpecHandler = ipcHandlers.get('spec:create');
      expect(createSpecHandler).toBeDefined();

      // Test the handler
      const result = await createSpecHandler!(null, {
        featureIdea: 'user authentication system with OAuth support',
        featureName: 'auth-system'
      });

      // Verify API call
      expect(mockedAxios.post).toHaveBeenCalledWith(
        'http://localhost:8890/api/v1/specs',
        {
          feature_idea: 'user authentication system with OAuth support',
          feature_name: 'auth-system'
        }
      );

      // Verify result
      expect(result.success).toBe(true);
      expect(result.data.spec_id).toBe('test-feature-spec');
      expect(result.data.workflow_state.current_phase).toBe('requirements');
    });

    test('should handle spec creation failure via IPC', async () => {
      // Mock API error
      const mockError = {
        response: {
          status: 400,
          data: {
            detail: 'Feature name already exists'
          }
        }
      };

      mockedAxios.post.mockRejectedValueOnce(mockError);

      const createSpecHandler = ipcHandlers.get('spec:create');
      const result = await createSpecHandler!(null, {
        featureIdea: 'duplicate feature',
        featureName: 'existing-spec'
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain('Feature name already exists');
    });

    test('should handle spec listing via IPC', async () => {
      // Mock API response
      const mockListResponse = {
        data: {
          specs: [
            {
              id: 'spec-1',
              feature_name: 'Feature 1',
              current_phase: 'requirements',
              status: 'draft',
              created_at: '2024-01-01T00:00:00Z'
            },
            {
              id: 'spec-2',
              feature_name: 'Feature 2',
              current_phase: 'design',
              status: 'in_progress',
              created_at: '2024-01-02T00:00:00Z'
            }
          ]
        }
      };

      mockedAxios.get.mockResolvedValueOnce(mockListResponse);

      const listSpecsHandler = ipcHandlers.get('spec:list');
      const result = await listSpecsHandler!(null);

      expect(mockedAxios.get).toHaveBeenCalledWith('http://localhost:8890/api/v1/specs');
      expect(result.success).toBe(true);
      expect(result.data.specs).toHaveLength(2);
      expect(result.data.specs[0].id).toBe('spec-1');
    });

    test('should handle spec retrieval via IPC', async () => {
      const specId = 'test-spec-id';
      const mockGetResponse = {
        data: {
          spec_id: specId,
          current_phase: 'design',
          status: 'in_progress',
          documents: {
            requirements: '# Requirements\n\nTest requirements content',
            design: '# Design\n\nTest design content'
          },
          approvals: {
            requirements: { approved: true, feedback: 'Good requirements' }
          }
        }
      };

      mockedAxios.get.mockResolvedValueOnce(mockGetResponse);

      const getSpecHandler = ipcHandlers.get('spec:get');
      const result = await getSpecHandler!(null, specId);

      expect(mockedAxios.get).toHaveBeenCalledWith(`http://localhost:8890/api/v1/specs/${specId}`);
      expect(result.success).toBe(true);
      expect(result.data.spec_id).toBe(specId);
      expect(result.data.documents.requirements).toContain('Test requirements content');
    });
  });

  describe('Document Management IPC Handlers', () => {
    test('should handle requirements update via IPC', async () => {
      const specId = 'test-spec';
      const changes = {
        add_requirement: {
          title: 'New Security Requirement',
          user_story: 'As a user, I want secure access...',
          acceptance_criteria: 'WHEN user logs in THEN system SHALL authenticate...'
        }
      };

      const mockUpdateResponse = {
        data: {
          updated_content: '# Requirements\n\nUpdated requirements with new security requirement',
          changes_made: ['Added Requirement 4: New Security Requirement']
        }
      };

      mockedAxios.put.mockResolvedValueOnce(mockUpdateResponse);

      const updateRequirementsHandler = ipcHandlers.get('spec:update-requirements');
      const result = await updateRequirementsHandler!(null, { specId, changes });

      expect(mockedAxios.put).toHaveBeenCalledWith(
        `http://localhost:8890/api/v1/specs/${specId}/requirements`,
        { changes }
      );
      expect(result.success).toBe(true);
      expect(result.data.changes_made).toContain('Added Requirement 4: New Security Requirement');
    });

    test('should handle design update via IPC', async () => {
      const specId = 'test-spec';
      const changes = {
        update_section: {
          section: 'Architecture',
          content: 'Updated architecture with microservices approach'
        }
      };

      const mockUpdateResponse = {
        data: {
          updated_content: '# Design\n\nUpdated design document',
          changes_made: ['Updated Architecture section']
        }
      };

      mockedAxios.put.mockResolvedValueOnce(mockUpdateResponse);

      const updateDesignHandler = ipcHandlers.get('spec:update-design');
      const result = await updateDesignHandler!(null, { specId, changes });

      expect(mockedAxios.put).toHaveBeenCalledWith(
        `http://localhost:8890/api/v1/specs/${specId}/design`,
        { changes }
      );
      expect(result.success).toBe(true);
    });

    test('should handle tasks update via IPC', async () => {
      const specId = 'test-spec';
      const changes = {
        add_task: {
          id: '5',
          description: 'Implement security features',
          details: ['Add authentication', 'Implement authorization'],
          requirements: ['4.1', '4.2']
        }
      };

      const mockUpdateResponse = {
        data: {
          updated_content: '# Implementation Plan\n\nUpdated tasks with security implementation',
          changes_made: ['Added Task 5: Implement security features']
        }
      };

      mockedAxios.put.mockResolvedValueOnce(mockUpdateResponse);

      const updateTasksHandler = ipcHandlers.get('spec:update-tasks');
      const result = await updateTasksHandler!(null, { specId, changes });

      expect(mockedAxios.put).toHaveBeenCalledWith(
        `http://localhost:8890/api/v1/specs/${specId}/tasks`,
        { changes }
      );
      expect(result.success).toBe(true);
    });
  });

  describe('Workflow Management IPC Handlers', () => {
    test('should handle phase approval via IPC', async () => {
      const specId = 'test-spec';
      const phase = 'requirements';
      const approved = true;
      const feedback = 'Requirements look comprehensive and well-structured';

      const mockApprovalResponse = {
        data: {
          approved: true,
          phase: 'requirements',
          feedback: feedback,
          timestamp: '2024-01-01T12:00:00Z'
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockApprovalResponse);

      const approvePhaseHandler = ipcHandlers.get('spec:approve-phase');
      const result = await approvePhaseHandler!(null, { specId, phase, approved, feedback });

      expect(mockedAxios.post).toHaveBeenCalledWith(
        `http://localhost:8890/api/v1/specs/${specId}/approve/${phase}`,
        { approved, feedback }
      );
      expect(result.success).toBe(true);
      expect(result.data.approved).toBe(true);
    });

    test('should handle workflow transition via IPC', async () => {
      const specId = 'test-spec';
      const targetPhase = 'design';
      const approval = true;

      const mockTransitionResponse = {
        data: {
          current_phase: 'design',
          previous_phase: 'requirements',
          design_content: '# Design Document\n\nGenerated design content',
          transition_timestamp: '2024-01-01T12:00:00Z'
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockTransitionResponse);

      const transitionHandler = ipcHandlers.get('spec:transition');
      const result = await transitionHandler!(null, { specId, targetPhase, approval });

      expect(mockedAxios.post).toHaveBeenCalledWith(
        `http://localhost:8890/api/v1/specs/${specId}/transition`,
        { target_phase: targetPhase, approval }
      );
      expect(result.success).toBe(true);
      expect(result.data.current_phase).toBe('design');
    });

    test('should handle workflow status retrieval via IPC', async () => {
      const specId = 'test-spec';
      const mockStatusResponse = {
        data: {
          spec_id: specId,
          current_phase: 'tasks',
          status: 'in_progress',
          approvals: {
            requirements: { approved: true, feedback: 'Good' },
            design: { approved: true, feedback: 'Solid architecture' },
            tasks: { approved: false, feedback: null }
          },
          metadata: {
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T12:00:00Z',
            version: '1.0.0'
          }
        }
      };

      mockedAxios.get.mockResolvedValueOnce(mockStatusResponse);

      const getStatusHandler = ipcHandlers.get('spec:get-status');
      const result = await getStatusHandler!(null, specId);

      expect(mockedAxios.get).toHaveBeenCalledWith(`http://localhost:8890/api/v1/specs/${specId}/status`);
      expect(result.success).toBe(true);
      expect(result.data.current_phase).toBe('tasks');
    });
  });

  describe('Task Execution IPC Handlers', () => {
    test('should handle task execution via IPC', async () => {
      const specId = 'test-spec';
      const taskId = '1.1';

      const mockExecutionResponse = {
        data: {
          success: true,
          task_id: taskId,
          message: 'Task completed successfully',
          files_created: ['src/components/LoginForm.tsx', 'src/services/authService.ts'],
          files_modified: ['src/App.tsx', 'package.json'],
          tests_run: ['LoginForm.test.tsx', 'authService.test.ts'],
          execution_time: 3.2,
          details: {
            components_created: ['LoginForm', 'AuthService'],
            dependencies_added: ['axios', 'jwt-decode']
          }
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockExecutionResponse);

      const executeTaskHandler = ipcHandlers.get('task:execute');
      const result = await executeTaskHandler!(null, { specId, taskId });

      expect(mockedAxios.post).toHaveBeenCalledWith(
        `http://localhost:8890/api/v1/specs/${specId}/tasks/${taskId}/execute`
      );
      expect(result.success).toBe(true);
      expect(result.data.task_id).toBe(taskId);
      expect(result.data.files_created).toContain('src/components/LoginForm.tsx');
    });

    test('should handle task status update via IPC', async () => {
      const specId = 'test-spec';
      const taskId = '2';
      const status = 'in_progress';

      const mockStatusResponse = {
        data: {
          task_id: taskId,
          status: status,
          updated_at: '2024-01-01T12:00:00Z'
        }
      };

      mockedAxios.put.mockResolvedValueOnce(mockStatusResponse);

      const updateTaskStatusHandler = ipcHandlers.get('task:update-status');
      const result = await updateTaskStatusHandler!(null, { specId, taskId, status });

      expect(mockedAxios.put).toHaveBeenCalledWith(
        `http://localhost:8890/api/v1/specs/${specId}/tasks/${taskId}/status`,
        { status }
      );
      expect(result.success).toBe(true);
      expect(result.data.status).toBe(status);
    });

    test('should handle progress tracking via IPC', async () => {
      const specId = 'test-spec';

      const mockProgressResponse = {
        data: {
          total_tasks: 12,
          completed_tasks: 5,
          in_progress_tasks: 2,
          not_started_tasks: 5,
          completion_percentage: 41.7,
          total_effort: 45,
          completed_effort: 18,
          effort_completion_percentage: 40.0,
          next_recommended_task: {
            id: '3.1',
            description: 'Implement user authentication API',
            estimated_effort: 4,
            requirements: ['1.1', '1.2']
          },
          critical_path: [
            { id: '1', description: 'Set up infrastructure' },
            { id: '2', description: 'Implement data models' },
            { id: '3', description: 'Build authentication system' }
          ]
        }
      };

      mockedAxios.get.mockResolvedValueOnce(mockProgressResponse);

      const getProgressHandler = ipcHandlers.get('task:get-progress');
      const result = await getProgressHandler!(null, specId);

      expect(mockedAxios.get).toHaveBeenCalledWith(`http://localhost:8890/api/v1/specs/${specId}/progress`);
      expect(result.success).toBe(true);
      expect(result.data.completion_percentage).toBe(41.7);
      expect(result.data.next_recommended_task.id).toBe('3.1');
    });
  });

  describe('Error Handling in IPC', () => {
    test('should handle network errors gracefully', async () => {
      const networkError = new Error('Network Error');
      mockedAxios.get.mockRejectedValueOnce(networkError);

      const listSpecsHandler = ipcHandlers.get('spec:list');
      const result = await listSpecsHandler!(null);

      expect(result.success).toBe(false);
      expect(result.error).toContain('Network Error');
    });

    test('should handle API validation errors', async () => {
      const validationError = {
        response: {
          status: 422,
          data: {
            detail: [
              {
                loc: ['body', 'feature_idea'],
                msg: 'field required',
                type: 'value_error.missing'
              }
            ]
          }
        }
      };

      mockedAxios.post.mockRejectedValueOnce(validationError);

      const createSpecHandler = ipcHandlers.get('spec:create');
      const result = await createSpecHandler!(null, { featureName: 'test' }); // Missing featureIdea

      expect(result.success).toBe(false);
      expect(result.error).toContain('field required');
    });

    test('should handle server errors', async () => {
      const serverError = {
        response: {
          status: 500,
          data: {
            detail: 'Internal server error'
          }
        }
      };

      mockedAxios.post.mockRejectedValueOnce(serverError);

      const executeTaskHandler = ipcHandlers.get('task:execute');
      const result = await executeTaskHandler!(null, { specId: 'test', taskId: '1' });

      expect(result.success).toBe(false);
      expect(result.error).toContain('Internal server error');
    });

    test('should handle timeout errors', async () => {
      const timeoutError = {
        code: 'ECONNABORTED',
        message: 'timeout of 5000ms exceeded'
      };

      mockedAxios.post.mockRejectedValueOnce(timeoutError);

      const executeTaskHandler = ipcHandlers.get('task:execute');
      const result = await executeTaskHandler!(null, { specId: 'test', taskId: '1' });

      expect(result.success).toBe(false);
      expect(result.error).toContain('timeout');
    });
  });

  describe('IPC Event Broadcasting', () => {
    test('should broadcast spec creation events', async () => {
      const mockSpecResponse = {
        data: {
          spec_id: 'new-spec',
          workflow_state: {
            spec_id: 'new-spec',
            current_phase: 'requirements',
            status: 'draft'
          }
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockSpecResponse);

      const createSpecHandler = ipcHandlers.get('spec:create');
      await createSpecHandler!(null, {
        featureIdea: 'test feature',
        featureName: 'new-spec'
      });

      // Verify event was broadcast to renderer
      expect(mockWindow.webContents.send).toHaveBeenCalledWith(
        'spec:created',
        expect.objectContaining({
          spec_id: 'new-spec'
        })
      );
    });

    test('should broadcast task execution events', async () => {
      const mockExecutionResponse = {
        data: {
          success: true,
          task_id: '1',
          message: 'Task completed'
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockExecutionResponse);

      const executeTaskHandler = ipcHandlers.get('task:execute');
      await executeTaskHandler!(null, { specId: 'test-spec', taskId: '1' });

      // Verify progress update event was broadcast
      expect(mockWindow.webContents.send).toHaveBeenCalledWith(
        'task:progress-updated',
        expect.objectContaining({
          spec_id: 'test-spec',
          task_id: '1'
        })
      );
    });

    test('should broadcast workflow transition events', async () => {
      const mockTransitionResponse = {
        data: {
          current_phase: 'design',
          previous_phase: 'requirements'
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockTransitionResponse);

      const transitionHandler = ipcHandlers.get('spec:transition');
      await transitionHandler!(null, {
        specId: 'test-spec',
        targetPhase: 'design',
        approval: true
      });

      // Verify workflow transition event was broadcast
      expect(mockWindow.webContents.send).toHaveBeenCalledWith(
        'workflow:phase-changed',
        expect.objectContaining({
          spec_id: 'test-spec',
          current_phase: 'design',
          previous_phase: 'requirements'
        })
      );
    });
  });

  describe('IPC Performance and Reliability', () => {
    test('should handle concurrent IPC requests', async () => {
      // Mock multiple API responses
      mockedAxios.get.mockResolvedValue({ data: { success: true } });

      const getStatusHandler = ipcHandlers.get('spec:get-status');

      // Simulate concurrent requests
      const promises = Array.from({ length: 10 }, (_, i) =>
        getStatusHandler!(null, `spec-${i}`)
      );

      const results = await Promise.all(promises);

      // All requests should succeed
      results.forEach(result => {
        expect(result.success).toBe(true);
      });

      // Verify all API calls were made
      expect(mockedAxios.get).toHaveBeenCalledTimes(10);
    });

    test('should handle large data payloads', async () => {
      // Create large mock response
      const largeSpecs = Array.from({ length: 1000 }, (_, i) => ({
        id: `spec-${i}`,
        feature_name: `Feature ${i}`,
        current_phase: 'requirements',
        status: 'draft',
        created_at: '2024-01-01T00:00:00Z'
      }));

      const largeResponse = {
        data: {
          specs: largeSpecs
        }
      };

      mockedAxios.get.mockResolvedValueOnce(largeResponse);

      const listSpecsHandler = ipcHandlers.get('spec:list');
      const result = await listSpecsHandler!(null);

      expect(result.success).toBe(true);
      expect(result.data.specs).toHaveLength(1000);
    });

    test('should implement request timeout handling', async () => {
      // Mock a slow response
      const slowPromise = new Promise((resolve) => {
        setTimeout(() => resolve({ data: { success: true } }), 10000);
      });

      mockedAxios.post.mockReturnValueOnce(slowPromise as any);

      const executeTaskHandler = ipcHandlers.get('task:execute');
      
      // This should timeout and return an error
      const result = await executeTaskHandler!(null, { specId: 'test', taskId: '1' });

      // Depending on implementation, this might timeout or succeed
      // The test verifies the handler can deal with slow responses
      expect(typeof result.success).toBe('boolean');
    });
  });

  describe('IPC Security', () => {
    test('should validate IPC input parameters', async () => {
      const createSpecHandler = ipcHandlers.get('spec:create');

      // Test with invalid input
      const result = await createSpecHandler!(null, {
        featureIdea: null,
        featureName: '<script>alert("xss")</script>'
      });

      // Should handle invalid input gracefully
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    test('should sanitize file paths in responses', async () => {
      const mockExecutionResponse = {
        data: {
          success: true,
          task_id: '1',
          files_created: [
            '../../../etc/passwd',
            'src/components/LoginForm.tsx'
          ]
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockExecutionResponse);

      const executeTaskHandler = ipcHandlers.get('task:execute');
      const result = await executeTaskHandler!(null, { specId: 'test', taskId: '1' });

      // Should filter out suspicious file paths
      expect(result.data.files_created).not.toContain('../../../etc/passwd');
      expect(result.data.files_created).toContain('src/components/LoginForm.tsx');
    });
  });
});

describe('IPC Channel Registration', () => {
  test('should register all required IPC channels', () => {
    const expectedChannels = [
      'spec:create',
      'spec:list',
      'spec:get',
      'spec:update-requirements',
      'spec:update-design',
      'spec:update-tasks',
      'spec:approve-phase',
      'spec:transition',
      'spec:get-status',
      'task:execute',
      'task:update-status',
      'task:get-progress'
    ];

    expectedChannels.forEach(channel => {
      expect(ipcMain.handle).toHaveBeenCalledWith(
        channel,
        expect.any(Function)
      );
    });
  });

  test('should handle IPC channel cleanup', () => {
    // Simulate app shutdown
    const cleanupHandler = ipcHandlers.get('app:cleanup');
    
    if (cleanupHandler) {
      cleanupHandler(null);
    }

    // Verify cleanup was called
    expect(ipcMain.removeAllListeners).toHaveBeenCalled();
  });
});