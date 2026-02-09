# Logseq Profile

This profile covers Logseq integration via MCP and the `lsq` CLI.

**IMPORTANT**: Do NOT update Logseq journal entries unless the user specifically instructs you to do so. The journal is
the user's personal knowledge base - only write to it when explicitly asked.

## Connection Setup

The Logseq MCP server connects to Logseq's HTTP API. Requirements:

- Logseq must have HTTP API enabled (Settings → Features → Enable HTTP API)
- An authentication token must be configured in Logseq
- The `LOGSEQ_TOKEN` environment variable must be set before starting Claude Code
- Default port: 12315

**SSH Tunneling Note**: If connecting via SSH tunnel from WSL2, the tunnel must be established from Windows
(PowerShell), not WSL2. WSL2 has a separate network namespace and cannot reach Windows localhost services via SSH `-R`
forwarding.

## Journal Page Names

Journal pages use the format `YYYY-MM-DD` (e.g., `2025-12-04`). This is important when:

- Searching for specific dates
- Using `getJournalSummary` with date ranges

## MCP Tool Usage

**Prefer CLI over MCP**: The MCP tools are buggy and often waste tokens. When you know the specific page you need, use
`lsq` CLI commands instead (see "Logseq CLI" section below).

**Working Tools** (use sparingly):

- `searchPages` - Find pages by name (useful for discovery)
- `getAllPages` - List all pages (returns page metadata including UUIDs)
- `smartQuery` - Natural language queries (results vary)

**Avoid These Tools**:

- `getJournalSummary` - Wastes tokens returning large amounts of content; often doesn't return what you need. Use
  `just lsq-blocks '<page>'` instead.
- `getPage` - Has a regex bug with date-formatted page names (e.g., `2025-12-04` causes "Invalid regular expression"
  error). Use `just lsq-blocks '<page>'` instead.
- `getBlock` - May not find blocks by page UUID

**Use With Caution**:

- `addJournalContent` - Only use YYYY-MM-DD date format (e.g., "2025-12-09"). Natural language dates like "dec 9th,
  2025" fail with "Page not found". **Important**: This appends content at the end of the page, not under a specific
  item. To add content under a specific block, use `just lsq-reply <uuid> '<content>'` instead.

## Logseq Conventions

**Task Markers**:

- `NOW` - Active/in-progress tasks
- `LATER` - Deferred tasks
- `DONE` - Completed tasks

**Structure**:

- Journal entries are organized under headings (e.g., `### [[Clients/FHDA]]`)
- Links use double brackets: `[[Page Name]]`
- Nested content uses tab indentation (Logseq's internal format)

## Common Operations

**Reading a Page**:

```bash
# Get all blocks on a page as a tree structure
just lsq-blocks '2025-12-09'           # Journal page
just lsq-blocks 'Project Notes'         # Regular page
```

**Adding Content Under a Specific Block**:

When adding content to a specific location (e.g., under an existing journal item):

1. First, get the page blocks to find the target block's UUID:
   ```bash
   just lsq-blocks '2025-12-09'
   ```
2. Use `lsq reply` with a heredoc to add content as a child of that block:
   ```bash
   poetry run lsq reply '<uuid>' <<'EOF'
   Content with `backticks` and special characters preserved
   EOF
   ```

**IMPORTANT - Always Use Heredocs**: Always use quoted heredocs (`<<'EOF'`) for content. The single quotes around EOF
prevent all shell expansion, ensuring backticks, quotes, and special characters are preserved exactly. Never pass
content as a command-line argument.

**Code Blocks Over Inline Backticks**: When documenting commands or procedures, prefer fenced code blocks as sub-bullets
rather than inline backticks. For example, instead of "run `efsmgr -d <file>` to decrypt", use a heading like "**To
Decrypt**:" followed by a child block containing a \`\`\`bash code block.

**Adding Content to End of Page** (less precise):

Only use `addJournalContent` when you want to append at the page level:

```
mcp__logseq__addJournalContent with content and date="2025-12-09"
```

**Important**: Use YYYY-MM-DD format for dates, not natural language.

## Known MCP Limitations

- **No edit/delete capability**: The MCP tools can only add content, not modify or delete existing blocks.
- **Hierarchical content**: `addJournalContent` may not preserve nested block structure correctly.

## Logseq CLI (`lsq`)

The `lsq` CLI extends Logseq functionality beyond what the MCP server provides. It supports raw Datalog queries, block
editing, and change detection.

**Available Commands** (via `just`):

| Command                                      | Description                          |
| -------------------------------------------- | ------------------------------------ |
| `just lsq-query '<datalog>'`                 | Run a raw Datalog query              |
| `just lsq-recent [MINUTES]`                  | Get pages modified in last N minutes |
| `just lsq-blocks '<page>'`                   | Get all blocks on a page as tree     |
| `just lsq-update <uuid> '<text>'`            | Update a block's content             |
| `just lsq-remove <uuid>`                     | Delete a block (with confirmation)   |
| `just lsq-reply <uuid> '<text>'`             | Reply to a block (insert as child)   |
| `just lsq-watch [INTERVAL]`                  | Poll for changes every N seconds     |
| `just lsq-await [SINCE] [TIMEOUT]`           | Block until change occurs            |
| `just lsq-find '<page>' [OPTIONS]`           | Find blocks matching criteria        |
| `just lsq-section-uuid '<page>' '<heading>'` | Get UUID of a section heading        |
| `just lsq-bulk-update '<page>' [OPTIONS]`    | Bulk update blocks (use --dry-run!)  |

**Example Datalog Queries**:

```bash
# Find all page names
just lsq-query '[:find ?name :where [?p :block/name ?name]]'

# Find blocks with TODO marker
just lsq-query '[:find (pull ?b [*]) :where [?b :block/marker "TODO"]]'

# Find blocks updated since timestamp (ms)
just lsq-query '[:find ?content :in $ ?since :where [?b :block/content ?content] [?b :block/updated-at ?t] [(> ?t ?since)]]'
```

**Change Detection**:

Logseq tracks `updated-at` at the page level, not individual blocks. When any block changes, the page's timestamp
updates.

- `just lsq-recent` - Check what pages changed recently
- `just lsq-watch` - Continuously print changed pages
- `just lsq-await` - Block until a change occurs (long-poll style)

The `lsq-await` command is designed for event-driven workflows:

```bash
# First call - wait for changes from now
result=$(just lsq-await)

# Use returned timestamp for next call to avoid gaps
next_since=$(echo "$result" | jq -r '.timestamp')
result=$(just lsq-await "$next_since")
```

Returns JSON with `timestamp`, `since`, and `pages` array. Exit code 0 on changes, 2 on timeout.

**Replying to Blocks**:

Use `just lsq-reply <uuid> '<content>'` to insert a response as a child block:

```bash
# Reply as child (default)
just lsq-reply "abc-123-uuid" "Here's my response"

# Reply as sibling
just lsq-reply "abc-123-uuid" "Sibling response" true
```

**Bulk Operations**:

Use `lsq-find` and `lsq-bulk-update` for batch changes to blocks:

```bash
# Find all DONE blocks under a section
just lsq-find "My Page" --section "### PROD" --marker DONE

# Preview changing DONE to LATER (always use --dry-run first!)
just lsq-bulk-update "My Page" --section "### PROD" --marker DONE --set-marker LATER --dry-run

# Apply the changes
just lsq-bulk-update "My Page" --section "### PROD" --marker DONE --set-marker LATER

# Strip deployment IDs from content using regex
just lsq-bulk-update "My Page" --section "### Deployments" --replace '\s*\(\d+\)\s*$' --with ''

# Find blocks matching a pattern
just lsq-find "My Page" --pattern "error|failed"
```

Options for `find-blocks`:

- `--marker, -m` - Filter by task marker (DONE, LATER, TODO, etc.)
- `--section, -s` - Only search under this heading
- `--pattern, -p` - Regex pattern to match content
- `--raw, -r` - Output JSON

Options for `bulk-update`:

- `--marker, -m` - Filter blocks by marker
- `--section, -s` - Only update blocks under this heading
- `--set-marker` - Change the marker to this value
- `--replace` - Regex pattern to replace in content
- `--with` - Replacement string (required with --replace)
- `--dry-run, -n` - Preview changes without applying
