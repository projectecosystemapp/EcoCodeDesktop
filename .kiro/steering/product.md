# Product Overview

EcoCode is an early-access spec-driven engineering platform that orchestrates multi-agent AI workflows, manages encrypted project workspaces, and provides a desktop experience for human-in-the-loop software delivery.

## Core Features

- **Multi-agent AI orchestration**: Coordinates AI workflows for software development tasks
- **Encrypted workspace management**: Secure project workspaces with encryption at rest
- **Desktop client**: Electron-based application for local development
- **Spec-driven workflow**: Requirements → Design → Implementation task breakdown
- **AWS integrations**: Bedrock (AI), S3 (storage), Secrets Manager, Stripe (billing)

## Architecture

The system consists of:
- **Desktop app**: Electron + React frontend for user interaction
- **Orchestrator service**: Python FastAPI backend handling AI coordination and encryption
- **Local-first approach**: Runs locally with optional cloud connectivity

## Target Users

Early-access participants working on software development projects who need:
- AI-assisted development workflows
- Secure project management
- Spec-driven development processes
- Local control with cloud integration options