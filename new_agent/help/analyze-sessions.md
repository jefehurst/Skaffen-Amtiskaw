# just analyze-sessions

Analyze Claude Code session logs for correction patterns and instructional moments.

## Usage

```bash
just analyze-sessions        # Markdown report to stdout
just analyze-sessions-json   # JSON output
just analyze-sessions-save   # Save to reflect/analysis-YYYYMMDD.md
```

## What It Finds

The script looks for patterns indicating:

### Corrections

- "no, that's not..."
- "wrong"
- "actually..."
- "instead..."
- "don't do/ask/try..."

### Instructions

- "always..."
- "never..."
- "from now on..."
- "remember to..."
- "update your procedures/profile..."

### Frustration (potential repeated issues)

- "again" (high false positive rate)
- "I already explained..."

## Output Format (Markdown)

```markdown
# Session Analysis Report

**Generated**: 2025-12-17T10:28:15
**Total Findings**: 122

## Corrections (48)

### Pattern: `\binstead[,]?\s` (22 occurrences)

**Session**: `23ddab2e...`
**Time**: 2025-12-16T15:21:47

[user message excerpt]
```

## Output Format (JSON)

```json
[
  {
    "session_id": "23ddab2e-897c-4a0c-b260-e766021cd0fc",
    "timestamp": "2025-12-16T15:21:47.556Z",
    "category": "correction",
    "pattern": "\\binstead[,]?\\s",
    "user_message": "...",
    "context_before": "...",
    "context_after": "..."
  }
]
```

## Files

- Script: `scripts/analyze_sessions.py`
- Sessions: `~/.claude/projects/<project-path>/*.jsonl`
- Output: `reflect/analysis-YYYYMMDD.md`

## Related

- `just sessions-pending` - See which sessions are new/updated
- `just sessions-mark` - Mark sessions as reviewed after analysis
- `/reflect` command - Full reflection workflow
