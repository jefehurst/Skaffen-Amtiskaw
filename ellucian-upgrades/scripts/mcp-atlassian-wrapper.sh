#!/usr/bin/env bash
set -euo pipefail

# Source credentials - check multiple locations
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
USER_CREDS="${HOME}/.config/mcp-atlassian/credentials.env"

CREDS_FOUND=false

# Priority 1: Project-level local.env (gitignored)
if [[ -f "$PROJECT_ROOT/local.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$PROJECT_ROOT/local.env"
  set +a
  CREDS_FOUND=true
fi

# Priority 2: User-level credentials (from atlassian-setup.sh)
if [[ -f "$USER_CREDS" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$USER_CREDS"
  set +a
  CREDS_FOUND=true
fi

if [[ "$CREDS_FOUND" != "true" ]]; then
  echo "Error: No Atlassian credentials found." >&2
  echo "Run: just atlassian-setup" >&2
  exit 1
fi

# Run mcp-atlassian
exec poetry run mcp-atlassian "$@"
