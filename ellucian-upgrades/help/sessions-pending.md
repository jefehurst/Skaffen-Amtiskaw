# just sessions-pending

List session logs that are new or updated since last review.

## Usage

```bash
just sessions-pending
```

## Output

Tab-separated values (TSV):

```
STATUS  SESSION_ID  MTIME   SIZE
NEW 00d8ee78-e164-400f-ba29-3155a2e46313    2025-12-14T09:21    50176
UPDATED 23ddab2e-897c-4a0c-b260-e766021cd0fc    2025-12-17T10:40    2982248
```

| Column     | Description                                                   |
| ---------- | ------------------------------------------------------------- |
| STATUS     | `NEW` (not yet reviewed) or `UPDATED` (modified since review) |
| SESSION_ID | UUID of the session (filename without .jsonl)                 |
| MTIME      | Last modification time (ISO format)                           |
| SIZE       | File size in bytes (sessions < 1KB are filtered out)          |

## How It Works

Compares sessions in `~/.claude/projects/<project-path>/` against `reflect/reviewed.tsv`.

Sessions are considered pending if:

- Not in reviewed.tsv (NEW)
- Modified after the recorded review time (UPDATED)

## Related

- `just sessions-summary` - Quick counts only
- `just sessions-mark ID [N]` - Mark a session as reviewed
- `just analyze-sessions` - Run pattern analysis on sessions
