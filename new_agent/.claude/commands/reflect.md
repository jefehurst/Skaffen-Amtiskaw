# Reflection Mode

You are entering **reflection mode** - a structured self-improvement process where you analyze past sessions to identify
corrections, learnings, and patterns that should be internalized.

## Context

Load the reflection log first:

```
Read: reflect/LOG.md
```

This contains:

- Sessions already reviewed
- Adjustments already made
- Pattern library for identifying corrections
- Improvement targets (where to apply learnings)

## Process

### 1. Check Pending Sessions

First, see what needs review:

```bash
just sessions-summary    # Quick counts
just sessions-pending    # List new/updated sessions (TSV: STATUS ID MTIME SIZE)
```

The pending list shows only sessions that are new or modified since last review. This avoids re-processing.

### 2. Analyze Sessions

Run the analysis script on pending sessions:

```bash
just analyze-sessions         # All sessions, markdown report
just analyze-sessions-json    # JSON for filtering
```

Session logs are in: `~/.claude/projects/<project-path>/*.jsonl` (path varies by project location)

### 3. Identify Actionable Findings

Focus on:

- **Repeated corrections** - User said "I've told you before" or corrected the same thing multiple times
- **Explicit instructions** - "From now on...", "Always...", "Never...", "Update your procedures..."
- **Frustration signals** - "I already explained", "How many times", "We discussed this"

Filter out false positives:

- "again" usually means "repeat this please"
- "wrong" often describes external systems, not your errors
- "instead" in task descriptions isn't a correction

### 4. Apply Improvements

Choose the right target based on scope:

| Scope           | Target                  | Example                                          |
| --------------- | ----------------------- | ------------------------------------------------ |
| Project-wide    | `CLAUDE.md`             | "Always run tests before committing"             |
| Domain-specific | `profiles/*.md`         | "Ellucian uses numeric IDs, not KB prefix"       |
| Workflow        | `.claude/commands/*.md` | "Load STATUS.md first when entering client mode" |
| Client-specific | `clients/*/STATUS.md`   | Environment details (rarely used for learnings)  |

### 5. Mark Sessions Reviewed

After processing sessions, mark them as reviewed:

```bash
just sessions-mark <session-id> <findings-count>
# Example: just sessions-mark 23ddab2e-897c-4a0c-b260-e766021cd0fc 3
```

This updates `reflect/reviewed.tsv` so you won't re-process the same sessions.

### 6. Update the Log

After applying changes, update `reflect/LOG.md`:

1. Document adjustments in "Adjustments Made" section
2. Add any new patterns to "Pattern Library"
3. Note pending items for next reflection

## Available Tools

### Session Tracking

```bash
just sessions-summary              # Counts: total, reviewed, pending
just sessions-pending              # TSV list of new/updated sessions
just sessions-mark <id> [findings] # Mark session as reviewed
```

Tracking data: `reflect/reviewed.tsv`

### Session Analysis Script

```bash
just analyze-sessions              # Markdown report to stdout
just analyze-sessions-json         # JSON output
just analyze-sessions-save         # Save to reflect/analysis-YYYYMMDD.md
```

### Manual Session Review

To review a specific session in detail:

```bash
# Find sessions by summary
grep -l "summary" ~/.claude/projects/<project-path>/*.jsonl | \
  xargs -I{} sh -c 'echo "=== {} ===" && head -5 {}'

# Extract user messages from a session
cat ~/.claude/projects/<project-path>/<session-id>.jsonl | \
  python3 -c "import sys,json; [print(json.loads(l).get('message',{}).get('content','')[:200]) for l in sys.stdin if json.loads(l).get('message',{}).get('role')=='user']"
```

### Pattern Refinement

Edit `scripts/analyze_sessions.py` to:

- Add new correction patterns to `CORRECTION_PATTERNS`
- Add new instruction patterns to `INSTRUCTION_PATTERNS`
- Exclude false positives

## Improvement Targets Reference

### CLAUDE.md (System Prompt)

The main system prompt. Changes here affect all sessions.

**Sections to update**:

- "Development Philosophy" - General principles
- "Guidelines for AI Assistants" - Behavioral rules
- "Code Conventions" - Language-specific patterns

### Profiles

Domain-specific context loaded on trigger keywords.

**Each profile should have**:

- "Behavioral Corrections" section for accumulated learnings
- Specific procedures and conventions
- Cross-references to related profiles

**Profile structure**:

```markdown
## Behavioral Corrections

### [Date] - [Brief Topic]
**Problem**: What went wrong
**Correction**: The right approach
**Context**: Why this matters (optional)
```

### Slash Commands

Entry points for common workflows. Consider creating new commands for:

- Repeated multi-step processes
- Context loading sequences
- Workflows that benefit from standardization

## When to Run Reflection

1. **Weekly** - Quick scan for new patterns
2. **After context exhaustion** - Long sessions often contain corrections
3. **When prompted** - User says "I've told you this before"
4. **After major work** - New client onboarding, complex troubleshooting

## Output

After reflection, summarize:

1. Sessions reviewed (count and date range)
2. New findings (categorized)
3. Changes applied (with file paths)
4. Pending items for next reflection
