EcoCode – Development Guidelines

Audience: Experienced developers working on the EcoCode monorepo.
Scope: Details that are specific to this repository: build, configuration, testing, and development practices for the Desktop (Electron+React) and the Orchestrator (Python FastAPI).

Repository overview
- apps/desktop: Electron + React client (Vite renderer, esbuild/tsc main process)
- services/orchestrator: FastAPI service coordinating agents, encryption, and optional AWS integrations
- packages/shared: Shared TypeScript utilities (e.g., schema definitions) [future/placeholder]
- docs/: Setup and product docs. See docs/setup/local.md for end‑to‑end local setup
- ops/: Infra and runbooks

Core runtime versions
- Node.js: >= 20.11 (required by root package.json)
- Python: >= 3.11 for services/orchestrator (enforced by pyproject.toml)

Build and configuration
Desktop (apps/desktop)
- Install deps from repository root: npm install
- Start development stack (desktop + orchestrator): npm run dev
  - Runs apps/desktop dev (Vite on http://127.0.0.1:5173) and services/orchestrator via make -C services/orchestrator run
- Lint and typecheck TypeScript:
  - Lint: npm --prefix apps/desktop run lint
  - Typecheck: npm --prefix apps/desktop run typecheck
- Build desktop app bundles:
  - Renderer: npm --prefix apps/desktop run build:renderer
  - Main process: npm --prefix apps/desktop run build:main

Orchestrator (services/orchestrator)
- Virtualenv bootstrap (creates .venv and installs editable package with dev tools):
  - cd services/orchestrator
  - make bootstrap
- Run API locally (hot reload):
  - ECOCODE_MASTER_PASSPHRASE=... ECOCODE_PROJECTS_ROOT=... make run
  - Default bind: 127.0.0.1:8890
- Lint/Type-check:
  - make lint  (ruff + mypy -- strict profile in pyproject)
- Test:
  - make test  (pytest, testpaths=tests per pyproject)

Required environment
- ECOCODE_MASTER_PASSPHRASE: Required. Derives encryption keys; not persisted. Without it, settings initialization raises ValueError
- ECOCODE_PROJECTS_ROOT: Optional. Root scanned for candidate projects (defaults to repository CWD). Manager recognizes projects by presence of one of: package.json, pyproject.toml, requirements.txt, Cargo.toml, or a .git directory
- ECOCODE_ORCHESTRATOR_URL: Optional. Used by desktop to point at orchestrator (default http://127.0.0.1:8890)

AWS integration (optional)
The orchestrator autodetects credentials/region via boto3’s default chain. Explicit overrides (pydantic‑settings env prefix ECOCODE_AWS_):
- ECOCODE_AWS_REGION_NAME
- ECOCODE_AWS_PROFILE_NAME
- ECOCODE_AWS_WORKSPACE_BUCKET
- ECOCODE_AWS_USE_BEDROCK=true|false
- ECOCODE_AWS_USE_S3_SYNC=true|false
- ECOCODE_AWS_USE_SECRETS_MANAGER=true|false

Endpoint surface (orchestrator)
- GET /health → HealthResponse(status, version, timestamp)
- GET /projects → Discover projects under ECOCODE_PROJECTS_ROOT; returns list of ProjectInfo
- POST /workspaces { project_path } → Creates per‑project encrypted workspace beside the project, with suffix from Settings.workspace_suffix (default "__eco_workspace"). Writes workspace.json metadata
- POST /workspaces/{workspace_name}/documents { relative_path, content } → Encrypts and stores UTF‑8 text into the workspace with .enc suffix enforced
- GET /aws/status → Returns resolved AWS status (region/profile/identity, workspace bucket existence, and detected errors)

Python version gotcha (local bootstrap)
- pyproject.toml enforces Python >= 3.11. If a .venv already exists with an older interpreter (e.g., 3.9), make bootstrap will fail with a version error
- Fix:
  1) Remove the stale venv: rm -rf services/orchestrator/.venv
  2) Recreate with Python 3.11: PYTHON=python3.11 make -C services/orchestrator bootstrap
  3) If python3.11 is not available, install it (e.g., via pyenv: pyenv install 3.11.9 && pyenv local 3.11.9) and rerun bootstrap

Testing
Policy
- All production code changes in services/orchestrator should be covered by pytest unit and/or integration tests under services/orchestrator/tests
- Keep tests hermetic. For AWS, prefer mocking boto3 clients (see eco_api.aws.AWSClient). Avoid hitting real cloud resources in CI/local unit tests

How to run orchestrator tests (canonical)
- Ensure Python 3.11 venv: PYTHON=python3.11 make -C services/orchestrator bootstrap
- Run: make -C services/orchestrator test
  - This invokes pytest with options defined in pyproject.toml (addopts = -ra -q, testpaths = tests)

Adding a new pytest (example)
File: services/orchestrator/tests/test_health.py

from fastapi.testclient import TestClient
from eco_api.main import app

def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data.get("version"), str)
    assert "timestamp" in data

Notes
- This test exercises an endpoint that has no Settings dependency, so it runs without ECOCODE_MASTER_PASSPHRASE
- For endpoints that depend on Settings (e.g., /projects), set env vars inside the test via monkeypatch or os.environ

Verified smoke test (no external deps)
Given some environments may lack Python 3.11 or pytest, you can smoke‑test source‑importable modules using the standard library unittest without creating a venv or installing packages. Example below was executed and verified:

1) Create services/orchestrator/tests_std/test_logging.py

import logging
import unittest

class TestLogging(unittest.TestCase):
    def test_configure_logging_sets_level(self):
        from eco_api.logging import configure_logging
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        configure_logging(level=logging.DEBUG)
        self.assertEqual(logging.getLogger().level, logging.DEBUG)

if __name__ == "__main__":
    unittest.main()

2) Run it from services/orchestrator as project root so python can import eco_api directly from source:

cd services/orchestrator && python3 -m unittest discover -s tests_std -v

Observed output

Running the above produced the following on a clean checkout:

test_configure_logging_sets_level (test_logging.TestLogging.test_configure_logging_sets_level) ... ok
----------------------------------------------------------------------
Ran 1 test in 0.002s
OK

Desktop testing
- There is currently no configured JS test runner in apps/desktop. For unit tests, we recommend adopting Vitest with React Testing Library, colocating tests under src/**/*.test.tsx, and wiring scripts test and test:watch at apps/desktop/package.json. Keep this in sync with ESLint and TypeScript project references in tsconfig.base.json

Code style and quality
Python (services/orchestrator)
- Ruff (tool.ruff): line-length 100; rulesets: E,F,I,UP,B,ASYNC,RUF; ignore E501
- MyPy (tool.mypy): Python 3.11, strict, warn_return_any, show_error_codes
- Prefer Pydantic v2 idioms (BaseModel from pydantic, pydantic-settings for env config)
- Logging: eco_api.logging.configure_logging sets basic format: "%(asctime)s %(levelname)s [%(name)s] %(message)s"
- Security: Encryption uses AES‑256‑GCM with scrypt KDF; workspace metadata stores salt (base64). ECOCODE_MASTER_PASSPHRASE must be reproducible but never persisted

TypeScript (apps/desktop)
- ESLint + Prettier configured; run with npm --prefix apps/desktop run lint
- Type-only CI safety: npm --prefix apps/desktop run typecheck
- Prefer explicit types on public surfaces, React function components with FC avoided, hooks naming useXyz, and no implicit any

Operational notes
- Workspaces are created adjacent to the source project with suffix from Settings.workspace_suffix (default "__eco_workspace"). Example: /path/to/myapp__eco_workspace
- /aws/status intentionally does not fail the service; the endpoint collects best‑effort AWS context and reports errors list for UI guidance
- /projects discovery is a simple directory scan; avoid placing extremely large directories under ECOCODE_PROJECTS_ROOT to keep UI responsive

Troubleshooting quick hits
- Orchestrator fails on startup: Ensure ECOCODE_MASTER_PASSPHRASE is set. Example: export ECOCODE_MASTER_PASSPHRASE="strong phrase"
- Bootstrap fails with Python version error: Remove .venv and recreate with python3.11 (see Python version gotcha)
- Desktop fails to connect to orchestrator: Confirm it’s serving http://127.0.0.1:8890 and ECOCODE_ORCHESTRATOR_URL overrides if custom binding is used

Housekeeping
- Tests that reach out to AWS should be marked and skipped by default or fully mocked. Keep unit tests deterministic and fast
- Prefer small, composable modules with explicit dependencies so the desktop and orchestrator can evolve independently
