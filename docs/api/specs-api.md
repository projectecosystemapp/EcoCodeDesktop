# Spec-Driven Workflow API Documentation

## Overview

The Spec-Driven Workflow API provides endpoints for managing feature specifications through a structured three-phase development process: Requirements → Design → Tasks. This API enables automated workflow orchestration, document generation, and task execution with comprehensive progress tracking.

## Base URL

```
http://localhost:8890
```

## Authentication

Currently, the API uses the EcoCode master passphrase for encryption operations. No additional authentication is required for local development.

## API Endpoints

### Spec Management

#### Create New Spec

Creates a new specification from a feature idea.

```http
POST /specs
```

**Request Body:**
```json
{
  "feature_idea": "User authentication system with OAuth integration",
  "feature_name": "user-authentication"  // Optional: auto-generated if not provided
}
```

**Response:**
```json
{
  "id": "user-authentication-20240918",
  "feature_name": "user-authentication",
  "current_phase": "requirements",
  "status": "draft",
  "created_at": "2024-09-18T10:30:00Z",
  "updated_at": "2024-09-18T10:30:00Z",
  "progress": 0
}
```

**Status Codes:**
- `201 Created` - Spec created successfully
- `400 Bad Request` - Invalid request data
- `409 Conflict` - Spec with same name already exists
- `500 Internal Server Error` - Server error

#### List All Specs

Retrieves a list of all specifications.

```http
GET /specs
```

**Query Parameters:**
- `status` (optional) - Filter by status: `draft`, `in_review`, `approved`, `in_progress`, `completed`, `error`
- `phase` (optional) - Filter by phase: `requirements`, `design`, `tasks`, `execution`
- `limit` (optional) - Maximum number of results (default: 50)
- `offset` (optional) - Number of results to skip (default: 0)

**Response:**
```json
{
  "specs": [
    {
      "id": "user-authentication-20240918",
      "feature_name": "user-authentication",
      "current_phase": "requirements",
      "status": "draft",
      "created_at": "2024-09-18T10:30:00Z",
      "updated_at": "2024-09-18T10:30:00Z",
      "progress": 25
    }
  ],
  "total_count": 1
}
```

#### Get Spec Details

Retrieves detailed information about a specific specification.

```http
GET /specs/{spec_id}
```

**Path Parameters:**
- `spec_id` - Unique identifier for the specification

**Response:**
```json
{
  "id": "user-authentication-20240918",
  "feature_name": "user-authentication",
  "current_phase": "requirements",
  "status": "draft",
  "created_at": "2024-09-18T10:30:00Z",
  "updated_at": "2024-09-18T10:30:00Z",
  "progress": 25,
  "documents": {
    "requirements": "# Requirements Document\n\n## Introduction\n...",
    "design": null,
    "tasks": null
  },
  "approvals": {
    "requirements": null,
    "design": null,
    "tasks": null
  },
  "metadata": {
    "version": "1.0.0",
    "checksum": {
      "requirements": "abc123...",
      "design": null,
      "tasks": null
    }
  }
}
```

**Status Codes:**
- `200 OK` - Spec retrieved successfully
- `404 Not Found` - Spec not found
- `500 Internal Server Error` - Server error

### Document Management

#### Update Requirements Document

Updates the requirements document for a specification.

```http
PUT /specs/{spec_id}/requirements
```

**Request Body:**
```json
{
  "content": "# Requirements Document\n\n## Introduction\n...",
  "approve": false,  // Optional: whether to approve this version
  "feedback": "Please add more detail about error handling"  // Optional
}
```

**Response:**
```json
{
  "success": true,
  "message": "Requirements document updated successfully",
  "updated_at": "2024-09-18T11:00:00Z",
  "checksum": "def456..."
}
```

#### Update Design Document

Updates the design document for a specification.

```http
PUT /specs/{spec_id}/design
```

**Request Body:**
```json
{
  "content": "# Design Document\n\n## Overview\n...",
  "approve": true,
  "feedback": "Design looks good, ready for implementation"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Design document updated and approved",
  "updated_at": "2024-09-18T12:00:00Z",
  "checksum": "ghi789..."
}
```

#### Update Tasks Document

Updates the tasks document for a specification.

```http
PUT /specs/{spec_id}/tasks
```

**Request Body:**
```json
{
  "content": "# Implementation Plan\n\n- [ ] 1. Set up project structure\n...",
  "approve": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Tasks document updated and approved",
  "updated_at": "2024-09-18T13:00:00Z",
  "checksum": "jkl012..."
}
```

### Task Execution

#### Execute Task

Executes a specific task from the task list.

```http
POST /specs/{spec_id}/tasks/{task_id}/execute
```

**Path Parameters:**
- `spec_id` - Unique identifier for the specification
- `task_id` - Task identifier (e.g., "1.1", "2.3")

**Request Body:**
```json
{
  "task_description": "Optional override description for the task"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task executed successfully",
  "task_id": "1.1",
  "status": "completed",
  "execution_log": [
    "Starting task execution...",
    "Created project structure",
    "Added configuration files",
    "Task completed successfully"
  ]
}
```

#### Update Task Status

Updates the status of a specific task.

```http
PUT /specs/{spec_id}/tasks/{task_id}/status
```

**Request Body:**
```json
{
  "status": "completed"  // Values: not_started, in_progress, completed, blocked
}
```

**Response:**
```json
{
  "success": true,
  "message": "Task status updated",
  "task_id": "1.1",
  "status": "completed",
  "updated_at": "2024-09-18T14:00:00Z"
}
```

#### Get Progress

Retrieves progress information for a specification.

```http
GET /specs/{spec_id}/progress
```

**Response:**
```json
{
  "spec_id": "user-authentication-20240918",
  "total_tasks": 15,
  "completed_tasks": 8,
  "in_progress_tasks": 2,
  "not_started_tasks": 5,
  "blocked_tasks": 0,
  "progress_percentage": 53.3,
  "current_phase": "execution",
  "status": "in_progress"
}
```

### Approval Workflow

#### Approve Phase

Approves or rejects a workflow phase.

```http
POST /specs/{spec_id}/approve/{phase}
```

**Path Parameters:**
- `spec_id` - Unique identifier for the specification
- `phase` - Phase to approve: `requirements`, `design`, `tasks`

**Request Body:**
```json
{
  "approved": true,
  "feedback": "Requirements are comprehensive and well-structured"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Phase approved successfully",
  "phase": "requirements",
  "approved": true,
  "next_phase": "design"
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request data: missing required field 'feature_idea'"
}
```

### 404 Not Found
```json
{
  "detail": "Specification not found: invalid-spec-id"
}
```

### 409 Conflict
```json
{
  "detail": "Specification with name 'user-authentication' already exists"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "feature_idea"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error: unable to generate requirements document"
}
```

## Rate Limiting

The API implements rate limiting to prevent abuse:

- **General endpoints**: 100 requests per minute per IP
- **Task execution**: 10 requests per minute per IP
- **Document updates**: 20 requests per minute per IP

Rate limit headers are included in responses:
- `X-RateLimit-Limit` - Request limit per window
- `X-RateLimit-Remaining` - Remaining requests in current window
- `X-RateLimit-Reset` - Time when the rate limit resets

## Webhooks

The API supports webhooks for real-time notifications of spec events:

### Webhook Events

- `spec.created` - New specification created
- `spec.updated` - Specification updated
- `document.updated` - Document content updated
- `phase.approved` - Workflow phase approved
- `task.completed` - Task execution completed
- `spec.completed` - All tasks completed

### Webhook Payload Example

```json
{
  "event": "task.completed",
  "timestamp": "2024-09-18T14:00:00Z",
  "data": {
    "spec_id": "user-authentication-20240918",
    "task_id": "1.1",
    "task_description": "Set up project structure",
    "status": "completed",
    "execution_time_ms": 2500
  }
}
```

## SDK Examples

### Python SDK

```python
import requests

class EcoCodeClient:
    def __init__(self, base_url="http://localhost:8890"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def create_spec(self, feature_idea, feature_name=None):
        payload = {"feature_idea": feature_idea}
        if feature_name:
            payload["feature_name"] = feature_name
        
        response = self.session.post(f"{self.base_url}/specs", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_spec(self, spec_id):
        response = self.session.get(f"{self.base_url}/specs/{spec_id}")
        response.raise_for_status()
        return response.json()
    
    def execute_task(self, spec_id, task_id):
        response = self.session.post(
            f"{self.base_url}/specs/{spec_id}/tasks/{task_id}/execute",
            json={}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = EcoCodeClient()
spec = client.create_spec("User authentication system")
print(f"Created spec: {spec['id']}")
```

### JavaScript SDK

```javascript
class EcoCodeClient {
    constructor(baseUrl = 'http://localhost:8890') {
        this.baseUrl = baseUrl;
    }
    
    async createSpec(featureIdea, featureName = null) {
        const payload = { feature_idea: featureIdea };
        if (featureName) {
            payload.feature_name = featureName;
        }
        
        const response = await fetch(`${this.baseUrl}/specs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        return response.json();
    }
    
    async getSpec(specId) {
        const response = await fetch(`${this.baseUrl}/specs/${specId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        return response.json();
    }
    
    async executeTask(specId, taskId) {
        const response = await fetch(
            `${this.baseUrl}/specs/${specId}/tasks/${taskId}/execute`,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            }
        );
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        return response.json();
    }
}

// Usage
const client = new EcoCodeClient();
const spec = await client.createSpec('User authentication system');
console.log(`Created spec: ${spec.id}`);
```

## Best Practices

### 1. Workflow Management

- Always follow the sequential workflow: Requirements → Design → Tasks → Execution
- Obtain explicit approval for each phase before proceeding
- Use meaningful feature names and descriptions
- Provide detailed feedback during approval processes

### 2. Task Execution

- Execute tasks in the order specified in the task list
- Handle sub-tasks before marking parent tasks complete
- Monitor task execution logs for debugging
- Use appropriate task status updates

### 3. Error Handling

- Implement proper retry logic for transient failures
- Check response status codes and handle errors appropriately
- Use the detailed health endpoint for monitoring
- Log API interactions for debugging

### 4. Performance

- Use pagination for large spec lists
- Cache spec data when appropriate
- Monitor rate limits and implement backoff strategies
- Use webhooks for real-time updates instead of polling

### 5. Security

- Validate all input data before sending to the API
- Use HTTPS in production environments
- Implement proper authentication when available
- Sanitize user-provided content in documents