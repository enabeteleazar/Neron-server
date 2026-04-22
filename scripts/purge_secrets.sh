#!/usr/bin/env bash
set -euo pipefail

# Purge sensitive files from git history using git filter-branch (deprecated but available).
# WARNING: This rewrites history. Ensure you have backups and coordinate with team.

if [ -n "$(git status --porcelain)" ]; then
  echo "Working directory not clean. Commit or stash changes first." >&2
  exit 1
fi

BACKUP_BRANCH="backup/pre-purge-$(date +%Y%m%d%H%M%S)"
echo "Creating backup branch $BACKUP_BRANCH"
git branch "$BACKUP_BRANCH"

echo "Removing sensitive files from history..."
# List of paths to remove
paths=(
  "server/neron.yaml"
  "server/neron.yaml.bk"
  "client/homeassistant/config/secrets.yaml"
  "client/homeassistant/config/.storage"
)

# Build index-filter command
INDEX_FILTER_CMD=""
for p in "${paths[@]}"; do
  INDEX_FILTER_CMD+="git rm -r --cached --ignore-unmatch '$p'; "
done

# Run filter-branch
git filter-branch --force --index-filter "$INDEX_FILTER_CMD" --prune-empty --tag-name-filter cat -- --all

# Expire reflog and garbage collect
git for-each-ref --format='delete %(refname)' refs/original | git update-ref --stdin || true
git reflog expire --expire=now --all
git gc --prune=now --aggressive || true

echo "Purge complete. Inspect repo and then push --force to remotes if desired."

echo "IMPORTANT: Rotate all secrets that were removed from history. See /etc/neron/PR_DESCRIPTION.md for notes." 
