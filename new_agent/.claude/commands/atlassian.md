---
description: Diagnose Atlassian MCP connection and validate access
---

# Atlassian MCP Diagnostics

Load the MCP Atlassian profile for context:

```
profiles/mcp-atlassian.md
```

## Diagnostic Procedure

Run these checks in order:

### 1. Check MCP Server Status

Run `claude mcp list` to verify the atlassian server shows as connected.

If not connected:

- Verify `.mcp.json` exists and contains the atlassian config
- Try `claude mcp get atlassian` for details
- Check if there's a conflicting user-level config

### 2. Check MCP Logs

Find and read the latest MCP log file:

```
~/.cache/claude-cli-nodejs/<project-path>/mcp-logs-atlassian/
```

Look for:

- Connection errors
- Authentication failures
- Tool registration issues

### 3. Test Tool Access

Attempt to call `mcp__atlassian__getConfluenceSpaces` to verify tools are available.

If tools aren't available but server shows connected:

- Restart Claude Code completely
- Check `.claude/settings.local.json` for `enableAllProjectMcpServers: true`
- Verify no scope conflicts between user and project config

### 4. Validate Atlassian Access

If tools are available, test actual Atlassian connectivity:

- List Confluence spaces
- Get current user info via `mcp__atlassian__atlassianUserInfo`

## Quick Fixes

**Re-add the server:**

```bash
claude mcp remove atlassian --scope project
claude mcp add atlassian https://mcp.atlassian.com/v1/sse --scope project --transport sse
```

**Clear and restart:**

1. Exit Claude Code
2. Run `claude mcp list` from terminal to verify config
3. Start fresh session with `./start.sh`

## Report Findings

After running diagnostics, summarize:

1. Server connection status
2. Tool availability status
3. Actual Atlassian API access status
4. Any errors found in logs
5. Recommended fix if issues found
