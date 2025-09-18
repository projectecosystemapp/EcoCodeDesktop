#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
GITHUB_URL="https://github.com/projectecosystemapp/EcoCodeDesktop.git"
BRANCH="main"

cd "$REPO_DIR"

# Ensure we're in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: Not inside a git repository at $REPO_DIR" >&2
  exit 1
fi

# Ensure branch exists and is checked out
current_branch=$(git rev-parse --abbrev-ref HEAD)
if [[ "$current_branch" != "$BRANCH" ]]; then
  git checkout -B "$BRANCH"
fi

# Configure the origin remote
if git remote get-url origin >/dev/null 2>&1; then
  current_url=$(git remote get-url origin)
  if [[ "$current_url" != "$GITHUB_URL" ]]; then
    git remote set-url origin "$GITHUB_URL"
  fi
else
  git remote add origin "$GITHUB_URL"
fi

# Remove any other remotes to avoid pushing to the wrong place
for r in $(git remote); do
  if [[ "$r" != "origin" ]]; then
    git remote remove "$r" || true
  fi
done

# Stage all changes
git add -A

# Commit only if there are staged changes
if ! git diff --cached --quiet; then
  # Prefer a concise message, preserving history
  git commit -m "chore(repo): sync changes to projectecosystemapp/EcoCodeDesktop"
else
  echo "No staged changes to commit."
fi

# Push to origin/main and set upstream
if git rev-parse --verify "$BRANCH" >/dev/null 2>&1; then
  git push -u origin "$BRANCH"
else
  echo "Branch $BRANCH does not exist locally; creating and pushing."
  git checkout -b "$BRANCH"
  git push -u origin "$BRANCH"
fi

# Show final state
echo "--- Remotes ---"
git remote -v

echo "--- Latest commit ---"
git --no-pager log -1 --oneline

echo "--- Status ---"
git --no-pager status -s

echo "Done: pushed to $GITHUB_URL on branch $BRANCH"
