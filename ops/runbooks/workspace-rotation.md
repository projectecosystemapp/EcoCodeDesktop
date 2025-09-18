# Workspace Key Rotation Runbook

1. Notify the engineering channel that a rotation will be performed and schedule a maintenance window.
2. Backup the encrypted workspace directories and corresponding `workspace.json` metadata for all active projects.
3. For each workspace:
   - Decrypt critical artifacts while the current passphrase is available.
   - Regenerate a salt using the orchestrator's admin endpoint (future release) or manually via the Python console.
   - Update `workspace.json` with the new salt and timestamp.
4. Instruct users to restart the orchestrator after exporting the new `ECOCODE_MASTER_PASSPHRASE` variable.
5. Validate that encrypted reads succeed by opening a recent requirements document.
6. Document the rotation in the security logbook with the date, operator, and any anomalies.
