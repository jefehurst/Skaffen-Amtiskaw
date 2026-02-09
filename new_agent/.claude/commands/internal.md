---
description: Load internal context for operations and development work
---

Load the internal operations context.

1. Read `internal/STATUS.md` - the source of truth for current internal efforts
2. Note any profiles or additional context STATUS.md suggests loading
3. Load those domain profiles from `profiles/` as needed
4. Summarize the current status and active work

## Internal Mode Behavior

Once in internal mode, maintain careful documentation throughout the session:

### Event Logging

Log significant events to `internal/SESSION_LOG.md` as they occur:

- Commands run and their outcomes
- Research findings and sources
- Design decisions and rationale
- Files created or modified
- Experiments tried and results

Use this format for each entry:

```
### [HH:MM] - Brief description
**Action**: What was done
**Result**: What happened
**Notes**: Any observations or follow-up needed
```

### Status Updates

When work progresses significantly:

1. Update `internal/STATUS.md` with the new status
2. Move completed items to a "## Completed" section with date and summary
3. Add any new items discovered during work

### Note-Taking Discipline

- Capture exact outputs and error messages
- Record file paths and environment details
- Document what was tried even if it didn't work
- Note sources for research findings
- Keep a running log of decisions and their rationale
