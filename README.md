# EcoCodeDesktop

EcoCode is an early-access spec-driven engineering platform that orchestrates multi-agent AI workflows, manages encrypted project workspaces, and exposes a desktop experience tailored for human-in-the-loop software delivery. This repository hosts the desktop application, local orchestrator, and supporting services required to run the EcoCode MVP.

## Project Structure

```
EcoCode/
├── apps/
│   └── desktop/        # Electron + React desktop client
├── services/
│   └── orchestrator/   # Python FastAPI service coordinating agents & encryption
├── packages/
│   └── shared/         # Shared TypeScript utilities (e.g., schema definitions)
├── ops/
│   ├── infra/          # Infrastructure as code & deployment scripts
│   └── runbooks/       # Operational documentation
└── docs/               # Product documentation, specs, and architecture assets
```

Each component can be developed and deployed independently, but the MVP is intended to run locally with optional AWS connectivity for Bedrock, S3, Secrets Manager, and Stripe integrations.

## Getting Started

> **Note:** The MVP relies on API credentials for AWS Bedrock, AWS Secrets Manager, Amazon S3, and Stripe. Gather those credentials before configuring the orchestrator service. The setup script will halt and prompt for any missing configuration.

1. Install dependencies for both Node.js (>=20.11) and Python (>=3.11).
2. Bootstrap the monorepo by running `npm install` at the repository root. This installs shared tooling and sets up workspace links.
3. Bootstrap the orchestrator Python environment:
   - `cd services/orchestrator`
   - `make bootstrap` (creates .venv and installs dependencies)
4. Start both the desktop app and orchestrator: `npm run dev`

Detailed setup instructions and environment configuration steps live in `docs/setup/local.md`.

## Engineering Notes (2025-09-18)

- **Desktop linting parity (`apps/desktop/eslint.config.js`, `apps/desktop/package.json`)**: Migrated to the ESLint 9 flat config with `typescript-eslint` helper and explicit React hook rules. After pulling, run `npm install --workspace apps/desktop` (Node 20.11+) to ensure the new dev dependency is installed, then validate with `npm run lint:ts`.
- **Renderer state sync (`apps/desktop/src/renderer/App.tsx`)**: Added `selectedProject` to the `useEffect` dependency list so the active selection tracks new project metadata without triggering lint noise.
- **Python style & typing hardening (`services/orchestrator/eco_api/*`, `services/orchestrator/pyproject.toml`)**: Resolved Ruff findings (import order, union typing, datetime usage) and adopted `typing.Annotated` for FastAPI dependencies. The Bedrock client now uses structural typing for streamed responses, and MyPy ignores for `boto3/botocore` moved into `pyproject` overrides. Run `make -C services/orchestrator lint` followed by `make -C services/orchestrator test` inside the `.venv` (Python 3.13) to reproduce the clean pass.
- **Version alignment (`services/orchestrator/eco_api/__init__.py`, `services/orchestrator/pyproject.toml`, `CHANGELOG.md`)**: Bumped the library and package version to `0.1.1` to match the latest changelog entry. Tag releases only after the CHANGELOG, code version, and packaging metadata stay in lockstep.
- **Agent context & prerequisites**: The orchestrator virtualenv lives at `services/orchestrator/.venv` (activate before running `ruff`, `mypy`, or `pytest`). Desktop scripts expect the workspace root `npm install` to have been run and reuse the repo-level lockfile. Network access was required once to install `typescript-eslint`; future offline builds should vendor the package if mirroring is needed. All current tests (`make -C services/orchestrator test`) and linters pass after these updates.

## Contributing

- Follow the spec-driven workflow: capture requirements under `docs/specs/requirements`, author designs under `docs/specs/designs`, and break implementation tasks into `docs/specs/tasks`.
- All code must be accompanied by tests (unit or integration) to validate core behavior.
- Enforce formatting with `npm run lint` for TypeScript and `make lint` for Python components.

## License

This project is currently proprietary and distributed only to EcoCode early-access participants.
