# Local Environment Setup

This guide walks through configuring the EcoCode MVP for local development. The orchestrator service enforces strong encryption, so the master passphrase and AWS credentials must be supplied explicitly before the services can start.

## Prerequisites

- Node.js 20.11 or later
- npm 10+
- Python 3.11+
- Git
- AWS credentials with permissions for Bedrock, S3, and Secrets Manager (optional for fully local workflows)

## Directory Layout

Clone or copy the repository to a writable location. The orchestrator scans `ECOCODE_PROJECTS_ROOT` for candidate projects. By default this is the repository root, but you can override it to point to a workspace containing multiple projects.

```
export ECOCODE_PROJECTS_ROOT="$HOME/Projects"
```

## Secure Passphrase

The orchestrator requires `ECOCODE_MASTER_PASSPHRASE` to derive per-workspace encryption keys. Choose a strong passphrase and set it before running the service:

```
export ECOCODE_MASTER_PASSPHRASE="change_me_to_a_strong_phrase"
```

> **Important:** The passphrase is never persisted; losing it renders existing encrypted workspaces unreadable. Store it securely in a password manager.

## Python Environment

Bootstrap the orchestrator dependencies using the provided `Makefile`:

```
cd services/orchestrator
make bootstrap
```

To run the API in development mode:

```
ECOCODE_MASTER_PASSPHRASE=... ECOCODE_PROJECTS_ROOT=... make run
```

## Desktop Application

Install Node dependencies:

```
npm install
```

Launch the desktop client and the orchestrator together:

```
ECOCODE_MASTER_PASSPHRASE=... ECOCODE_PROJECTS_ROOT=... npm run dev
```

The script starts the Vite development server (renderer), builds the Electron main process with esbuild, waits for the renderer to become available, and launches the Electron shell. The desktop client communicates with the orchestrator over `http://127.0.0.1:8890` by default. Override the URL with:

```
export ECOCODE_ORCHESTRATOR_URL="https://localhost:9000"
```

## AWS Connectivity (Optional)

By default, the orchestrator will autodetect your AWS credentials and region using boto3’s default provider chain (e.g., credentials from AWS Toolkit/IDE or ~/.aws). You can verify detection at runtime:

```
curl http://127.0.0.1:8890/aws/status | jq
```

Provide the following environment variables to explicitly enable/override cloud syncing and managed secrets:

```
export ECOCODE_AWS_REGION_NAME="us-east-1"
export ECOCODE_AWS_WORKSPACE_BUCKET="ecocode-dev-workspaces"
export ECOCODE_AWS_USE_BEDROCK=true
export ECOCODE_AWS_USE_S3_SYNC=true
export ECOCODE_AWS_USE_SECRETS_MANAGER=true
```

When the orchestrator detects missing credentials, it will log descriptive guidance and skip cloud integrations until the environment is fully configured.

## Troubleshooting

- **Missing passphrase**: The orchestrator exits with `ECOCODE_MASTER_PASSPHRASE is required`. Set the variable and restart.
- **Permission errors**: Ensure the directories referenced by `ECOCODE_PROJECTS_ROOT` and generated workspaces are writable.
- **Electron fails to launch**: Confirm that the Vite dev server is available on `http://127.0.0.1:5173`, and delete the `apps/desktop/dist` folder if the build cache becomes inconsistent.
- **Workspace recovery**: Keep backups of `workspace.json` and the encrypted directories. Without the original passphrase, data cannot be decrypted.
