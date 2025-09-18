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

## Contributing

- Follow the spec-driven workflow: capture requirements under `docs/specs/requirements`, author designs under `docs/specs/designs`, and break implementation tasks into `docs/specs/tasks`.
- All code must be accompanied by tests (unit or integration) to validate core behavior.
- Enforce formatting with `npm run lint` for TypeScript and `make lint` for Python components.

## License

This project is currently proprietary and distributed only to EcoCode early-access participants.
