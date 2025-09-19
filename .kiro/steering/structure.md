# Project Structure

## Repository Organization

```
EcoCode/
├── apps/                    # Application frontends
│   └── desktop/            # Electron + React desktop client
│       ├── src/
│       │   ├── main/       # Electron main process (Node.js)
│       │   ├── renderer/   # React frontend (browser context)
│       │   └── shared/     # Shared types between main/renderer
│       ├── scripts/        # Build and development scripts
│       └── dist/           # Build output (main + renderer)
├── services/               # Backend services
│   └── orchestrator/       # Python FastAPI orchestration service
│       ├── eco_api/        # Main application package
│       │   ├── workspaces/ # Workspace management modules
│       │   └── security/   # Encryption and security utilities
│       └── tests/          # Test suites
├── packages/               # Shared libraries and utilities
│   └── shared/            # TypeScript shared utilities
├── ops/                   # Operations and infrastructure
│   ├── infra/             # Infrastructure as code
│   └── runbooks/          # Operational procedures
└── docs/                  # Documentation and specifications
    ├── setup/             # Setup and configuration guides
    └── specs/             # Spec-driven development artifacts
        ├── requirements/   # Product requirements
        ├── designs/       # Technical designs
        └── tasks/         # Implementation tasks
```

## Code Organization Patterns

### Desktop App (`apps/desktop/`)
- **Main Process** (`src/main/`): Electron backend, IPC handlers, system integration
- **Renderer Process** (`src/renderer/`): React components, UI state, API calls
- **Shared Types** (`src/shared/`): TypeScript interfaces shared between processes
- **Build Separation**: Main process (Node.js) and renderer (browser) have separate builds

### Orchestrator Service (`services/orchestrator/`)
- **Package Structure**: Single `eco_api` package with submodules
- **Domain Modules**: `workspaces/`, `security/` for logical separation
- **Configuration**: Centralized settings with Pydantic models
- **API Layer**: FastAPI routes with dependency injection pattern

## File Naming Conventions

### TypeScript/React
- **Components**: PascalCase (e.g., `ProjectList.tsx`, `App.tsx`)
- **Utilities**: camelCase (e.g., `apiClient.ts`, `store.ts`)
- **Types**: PascalCase interfaces in `types.ts` files
- **Config Files**: kebab-case (e.g., `eslint.config.js`, `vite.config.ts`)

### Python
- **Modules**: snake_case (e.g., `workspace_manager.py`, `crypto.py`)
- **Classes**: PascalCase (e.g., `WorkspaceManager`, `AWSClient`)
- **Functions/Variables**: snake_case following PEP 8
- **Constants**: UPPER_SNAKE_CASE

## Architecture Boundaries

### Process Separation
- **Electron Main**: System APIs, file operations, orchestrator communication
- **Electron Renderer**: UI rendering, user interactions, sandboxed environment
- **Orchestrator**: Business logic, encryption, AWS integrations, workspace management

### Data Flow
- **Desktop → Orchestrator**: HTTP API calls (port 8890)
- **Main ↔ Renderer**: IPC (Inter-Process Communication)
- **Orchestrator → AWS**: SDK calls for Bedrock, S3, Secrets Manager

### Security Boundaries
- **Renderer Sandbox**: No direct Node.js access, preload script for safe IPC
- **Workspace Encryption**: All workspace documents encrypted at rest
- **AWS Credentials**: Managed through standard AWS credential chain

## Development Workflow

### Spec-Driven Process
1. **Requirements** (`docs/specs/requirements/`): Capture user needs and acceptance criteria
2. **Designs** (`docs/specs/designs/`): Technical architecture and implementation plans  
3. **Tasks** (`docs/specs/tasks/`): Granular implementation work items

### Testing Strategy
- **Unit Tests**: Core business logic and utilities
- **Integration Tests**: API endpoints and service interactions
- **Manual Testing**: Desktop UI workflows and user experience

### Version Management
- **Lockstep Versioning**: Keep `package.json`, `pyproject.toml`, and `CHANGELOG.md` in sync
- **Semantic Versioning**: Major.Minor.Patch for all components
- **Git Tags**: Only after changelog, code, and packaging metadata align