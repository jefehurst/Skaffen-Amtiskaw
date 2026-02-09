#!/usr/bin/env bash
# atlassian-setup.sh - Configure Atlassian OAuth for mcp-atlassian
#
# Usage: ./atlassian-setup.sh
#
# Runs the mcp-atlassian OAuth wizard via container (podman or docker).
# After completion, outputs the MCP configuration for ~/.claude.json

set -euo pipefail

# Detect container runtime
if command -v podman &>/dev/null; then
  CONTAINER_CMD="podman"
elif command -v docker &>/dev/null; then
  CONTAINER_CMD="docker"
else
  cat >&2 <<'EOF'
ERROR: Neither podman nor docker found in PATH.

Install one of:
  - podman: https://podman.io/getting-started/installation
  - docker: https://docs.docker.com/get-docker/

EOF
  exit 1
fi

echo "=== Atlassian OAuth 2.0 Setup ==="
echo ""
echo "Using: $CONTAINER_CMD"
echo ""
echo "Prerequisites:"
echo "  1. Create an OAuth 2.0 app at: https://developer.atlassian.com/console/myapps/"
echo "  2. Set callback URL to: http://localhost:8080/callback"
echo "  3. Add these scopes to your app:"
echo "     - read:jira-work"
echo "     - write:jira-work"
echo "     - read:confluence-content.all"
echo "     - write:confluence-content"
echo "     - search:confluence"
echo ""
read -rp "Press Enter to continue (or Ctrl-C to cancel)..."
echo ""

# Run the OAuth wizard
echo "Starting OAuth wizard..."
echo ""
echo "========================================================================"
echo "The wizard will prompt for these values:"
echo ""
echo "Client ID & Secret:"
echo "  Found on the 'Settings' tab of your app at:"
echo "  https://developer.atlassian.com/console/myapps/"
echo ""
echo "Redirect URI:"
echo "  http://localhost:8080/callback"
echo ""
echo "Scopes (copy this line):"
echo "read:jira-work write:jira-work read:confluence-content.all write:confluence-content search:confluence offline_access"
echo "========================================================================"
echo ""

$CONTAINER_CMD run --rm -it \
  -p 8080:8080 \
  -v "${HOME}/.mcp-atlassian:/home/app/.mcp-atlassian" \
  ghcr.io/sooperset/mcp-atlassian:latest --oauth-setup -v

echo ""
echo "=== Setup Complete ==="
echo ""
echo "The wizard output above contains the MCP configuration."
echo ""
echo "To configure Claude Code, add to ~/.claude.json under \"mcpServers\":"
echo ""
cat <<EOF
{
  "atlassian": {
    "type": "stdio",
    "command": "$CONTAINER_CMD",
    "args": [
      "run", "--rm", "-i",
      "-v", "\${HOME}/.mcp-atlassian:/home/app/.mcp-atlassian",
      "-e", "CONFLUENCE_URL",
      "-e", "JIRA_URL",
      "-e", "ATLASSIAN_OAUTH_CLIENT_ID",
      "-e", "ATLASSIAN_OAUTH_CLIENT_SECRET",
      "-e", "ATLASSIAN_OAUTH_REDIRECT_URI",
      "-e", "ATLASSIAN_OAUTH_SCOPE",
      "-e", "ATLASSIAN_OAUTH_CLOUD_ID",
      "ghcr.io/sooperset/mcp-atlassian:latest"
    ],
    "env": {
      "CONFLUENCE_URL": "https://YOUR-SITE.atlassian.net/wiki",
      "JIRA_URL": "https://YOUR-SITE.atlassian.net",
      "ATLASSIAN_OAUTH_CLIENT_ID": "<from wizard>",
      "ATLASSIAN_OAUTH_CLIENT_SECRET": "<from wizard>",
      "ATLASSIAN_OAUTH_REDIRECT_URI": "http://localhost:8080/callback",
      "ATLASSIAN_OAUTH_SCOPE": "read:jira-work write:jira-work read:confluence-content.all write:confluence-content search:confluence offline_access",
      "ATLASSIAN_OAUTH_CLOUD_ID": "<from wizard>"
    }
  }
}
EOF
echo ""
echo "Replace the placeholder values with your actual credentials from the wizard output."
echo ""
