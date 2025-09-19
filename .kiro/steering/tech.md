# Technology Stack

## Frontend (Desktop App)
- **Framework**: Electron 31+ with React 18
- **Build**: Vite 5+ with TypeScript 5.5+
- **UI Library**: Mantine 7+ (components, hooks, notifications)
- **State Management**: Zustand 4+
- **Routing**: React Router DOM 6+
- **Icons**: Tabler Icons React 2+
- **HTTP Client**: Axios 1.7+

## Backend (Orchestrator Service)
- **Framework**: FastAPI 0.115+ with Python 3.11+
- **ASGI Server**: Uvicorn with standard extras
- **Validation**: Pydantic 2.8+ with Settings 2.2+
- **Encryption**: Cryptography 43+
- **AWS SDK**: Boto3 1.34+
- **Database**: SQLAlchemy 2+ with Alembic 1.13+
- **HTTP Client**: HTTPX 0.27+

## Development Tools
- **Package Management**: npm workspaces (Node 20.11+), Python venv with pip
- **Linting**: ESLint 9 (flat config) + typescript-eslint 8+, Ruff 0.5+ (Python)
- **Type Checking**: TypeScript strict mode, MyPy 1.11+ (Python strict)
- **Testing**: pytest 8.3+ with asyncio support
- **Formatting**: Prettier 3+ (TypeScript), Ruff (Python)

## Build System & Commands

### Root Level
```bash
npm install              # Bootstrap monorepo and install dependencies
npm run dev             # Start both desktop and orchestrator in parallel
npm run lint            # Run linting for both TypeScript and Python
```

### Desktop App (`apps/desktop/`)
```bash
npm run dev             # Start Vite dev server + Electron in development
npm run build           # Build renderer and main process for production
npm run lint            # ESLint with TypeScript parser
npm run typecheck       # TypeScript compilation check
```

### Orchestrator Service (`services/orchestrator/`)
```bash
make bootstrap          # Create venv and install dependencies
make run               # Start FastAPI server with uvicorn (port 8890)
make lint              # Run ruff check + mypy type checking
make test              # Run pytest test suite
```

## Configuration Standards
- **TypeScript**: ES2022 target, strict mode, ESNext modules with NodeNext resolution
- **Python**: Line length 100, Ruff linting (E, F, I, UP, B, ASYNC, RUF rules)
- **ESLint**: Flat config with typescript-eslint, react-hooks, react-refresh plugins
- **Ports**: Desktop dev server (5173), Orchestrator API (8890)

## Version Requirements
- Node.js >= 20.11.0
- Python >= 3.11
- All dependencies use specific minimum versions for stability