---
description: Load client context for support work
---

Load the client profile for **$ARGUMENTS** mode.

1. Read `clients/$ARGUMENTS/STATUS.md` - this is the source of truth for current issues
2. Note any profiles or additional context STATUS.md suggests loading (e.g., Banner, Ellucian, Runner)
3. Load those domain profiles from `profiles/` as needed
4. Summarize the current client status and active issues

If the client directory doesn't exist, list available clients from `clients/*/STATUS.md`.

## Client Mode Behavior

Once in client mode, maintain careful documentation throughout the session:

### Event Logging

Log significant events to `clients/$ARGUMENTS/SESSION_LOG.md` as they occur:

- Commands run and their outcomes
- Errors encountered and error messages (verbatim)
- Configuration changes made
- Files modified (with before/after if relevant)
- Decisions made and rationale

Use this format for each entry:

```
### [HH:MM] - Brief description
**Action**: What was done
**Result**: What happened
**Notes**: Any observations or follow-up needed
```

### Status Updates

When an issue is resolved or significantly progresses:

1. Update `clients/$ARGUMENTS/STATUS.md` with the resolution or new status
2. Move resolved issues to a "## Resolved Issues" section with date and summary
3. Add any new issues discovered during troubleshooting

### Note-Taking Discipline

- Capture exact error messages, not paraphrased versions
- Record file paths, hostnames, and environment details
- Note timestamps for correlation with logs
- Document what was tried even if it didn't work (prevents re-trying)
- If the user provides information verbally, confirm and log it
