# Atlassian MCP Profile

This profile documents MCP (Model Context Protocol) configuration, with specific focus on the Atlassian MCP integration.

## MCP Overview

MCP (Model Context Protocol) allows Claude Code to communicate with external services via standardized tool interfaces.
MCP servers expose tools that Claude can invoke during conversations.

### Key Concepts

| Term       | Description                                                                      |
| ---------- | -------------------------------------------------------------------------------- |
| MCP Server | A process that exposes tools via the MCP protocol                                |
| Transport  | Communication method: `stdio` (local process) or `sse` (HTTP Server-Sent Events) |
| Scope      | Where config lives: `user`, `project`, or `local`                                |
| Tools      | Functions exposed by the MCP server that Claude can call                         |

### Configuration Scopes

| Scope     | File                          | Use Case                             |
| --------- | ----------------------------- | ------------------------------------ |
| `user`    | `~/.claude.json`              | Personal servers across all projects |
| `project` | `.mcp.json` (project root)    | Shared with team via version control |
| `local`   | `.claude/settings.local.json` | Machine-specific, not committed      |

**Best Practice**: Use `project` scope for team-shared servers. The `.mcp.json` file is designed to be committed to
version control.

## CLI Commands

**CRITICAL**: Always use CLI commands to manage MCP servers. Manual file editing often fails silently.

```bash
# List configured servers and their status
claude mcp list

# Add a server (stdio transport - local process)
claude mcp add <name> <command> [args...] --scope project --transport stdio

# Add a server (sse transport - hosted service)
claude mcp add <name> <url> --scope project --transport sse

# Remove a server
claude mcp remove <name> --scope project

# Get details about a server
claude mcp get <name>

# Show help
claude mcp --help
```

## Atlassian MCP

### Recommended Setup: Hosted SSE

The hosted Atlassian MCP at `https://mcp.atlassian.com/v1/sse` is the recommended approach. It:

- Handles authentication via Atlassian's OAuth
- Requires no local dependencies
- Works reliably across environments

**Setup:**

```bash
claude mcp add atlassian https://mcp.atlassian.com/v1/sse --scope project --transport sse
```

This creates/updates `.mcp.json`:

```json
{
  "mcpServers": {
    "atlassian": {
      "type": "sse",
      "url": "https://mcp.atlassian.com/v1/sse"
    }
  }
}
```

### Available Tools

Once connected, these tools become available (prefixed with `mcp__atlassian__`):

**Confluence:**

- `getConfluenceSpaces` - List spaces
- `getPagesInConfluenceSpace` - List pages in a space
- `getConfluencePage` - Get page content
- `getConfluencePageDescendants` - Get child pages
- `createConfluencePage` - Create a new page
- `updateConfluencePage` - Update existing page
- `searchConfluenceUsingCql` - Search with CQL

**Jira:**

- `getJiraIssue` - Get issue details
- `createJiraIssue` - Create an issue
- `editJiraIssue` - Update an issue
- `searchJiraIssuesUsingJql` - Search with JQL
- `addCommentToJiraIssue` - Add a comment
- `transitionJiraIssue` - Change issue status

**General:**

- `search` - Unified search across Jira and Confluence
- `atlassianUserInfo` - Get current user info
- `getAccessibleAtlassianResources` - List accessible cloud instances

### Authentication

The hosted SSE server handles OAuth automatically. On first use:

1. Claude Code prompts for Atlassian authentication
2. Browser opens to Atlassian login
3. Tokens are stored securely by the hosted service

No local token management required.

## Troubleshooting

### Diagnostic Steps

1. **Check server status:**

   ```bash
   claude mcp list
   ```

   Should show `✓ Connected` for atlassian.

2. **Get detailed info:**

   ```bash
   claude mcp get atlassian
   ```

3. **Check MCP logs:**

   ```bash
   ls -lt ~/.cache/claude-cli-nodejs/-$(pwd | tr '/' '-')/mcp-logs-atlassian/
   cat ~/.cache/claude-cli-nodejs/-$(pwd | tr '/' '-')/mcp-logs-atlassian/<latest>.txt
   ```

4. **Verify project config:**

   ```bash
   cat .mcp.json
   ```

5. **Test tool access:** Ask Claude to "list confluence spaces" - should invoke `mcp__atlassian__getConfluenceSpaces`.

### Common Issues

#### "No MCP servers configured"

- Check `.mcp.json` exists in project root
- Verify format with `claude mcp get atlassian`
- Try removing and re-adding: `claude mcp remove atlassian -s project && claude mcp add ...`

#### Server shows "Connected" but tools unavailable

- Restart Claude Code completely (not just `/mcp`)
- Check `.claude/settings.local.json` has `enableAllProjectMcpServers: true`
- Verify no conflicting config at user level in `~/.claude.json`

#### "Failed to connect"

- For SSE: Check network connectivity to `mcp.atlassian.com`
- For stdio: Verify command exists and is executable
- Check logs for specific error messages

#### Tools not appearing after restart

- Run `/mcp` to reconnect
- Check that the project's `.mcp.json` is being read (not overridden by user config)
- Verify `enabledMcpjsonServers` includes "atlassian" in settings.local.json

### Local mcp-atlassian (Not Recommended)

The `mcp-atlassian` PyPI package can be used locally but has issues:

- Requires OAuth setup wizard (localhost callback complications in remote environments)
- Token management complexity
- Tools may not be injected properly into Claude's session

If you must use it:

```bash
poetry add mcp-atlassian
# Create wrapper script
cat > scripts/mcp-atlassian-wrapper.sh << 'EOF'
#!/usr/bin/env bash
cd /path/to/project
exec poetry run mcp-atlassian "$@"
EOF
chmod +x scripts/mcp-atlassian-wrapper.sh

# Add to MCP
claude mcp add atlassian /path/to/scripts/mcp-atlassian-wrapper.sh \
  --scope project --transport stdio \
  -e CONFLUENCE_URL=https://yoursite.atlassian.net/wiki \
  -e JIRA_URL=https://yoursite.atlassian.net
```

## Behavioral Corrections

### 2024-12-14 - Use CLI, not manual file editing

**Problem**: Manually editing `.mcp.json`, `~/.claude/settings.json`, and `~/.claude/.mcp.json` did not result in
working MCP connections, even when the JSON was valid. **Correction**: Always use `claude mcp add/remove` commands. The
CLI handles internal state in `~/.claude.json` that manual editing misses. **Context**: Spent significant time debugging
why manually-created configs weren't working. The `claude mcp add` command immediately worked.

### 2024-12-14 - Hosted SSE over local stdio

**Problem**: Local `mcp-atlassian` via stdio connected successfully (`hasTools: true` in logs) but tools were never
injected into Claude's available toolset. **Correction**: Use the hosted Atlassian MCP at
`https://mcp.atlassian.com/v1/sse` instead. It works reliably. **Context**: The hosted service handles authentication
and tool registration properly.

### 2024-12-14 - Check for scope conflicts

**Problem**: User-level MCP config in `~/.claude.json` can override or conflict with project-level `.mcp.json`.
**Correction**: Check both scopes when debugging. Remove user-level config if using project-level. **Context**: Had a
Docker-based atlassian config at user level conflicting with poetry-based project config.

## Confluence Content Guidelines

### Table of Contents

**Never use plaintext TOCs**. For articles with multiple sections, use the Confluence TOC macro.

When uploading via markdown format, plaintext TOCs will render as static text. Instead, use ADF format with the TOC
extension:

```json
{
  "type": "extension",
  "attrs": {
    "extensionType": "com.atlassian.confluence.macro.core",
    "extensionKey": "toc",
    "parameters": {"macroParams": {}}
  }
}
```

**When to include TOC**: Articles with 3+ heading sections benefit from a TOC widget.

**Placement**: After the attribution block and initial horizontal rule, before the first content section.

### Long Articles

For articles exceeding ~50 lines of content:

1. Include TOC macro after attribution
2. Use clear H2/H3 hierarchy
3. Add horizontal rules between major sections
