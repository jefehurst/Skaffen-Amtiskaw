---
description: Survey all status logs and present end-of-day summary
---

End-of-day status review. Survey all client STATUS.md files and present a concise summary.

## Instructions

1. **Read all client status files**:

   - Read each `clients/*/STATUS.md` file
   - Extract: client name, current issues, status, and any EOD deadlines

2. **Present summary with heading per client**: Format:

   ```
   ## [Client Name]
   - **Status**: [Active/Waiting/Resolved]
   - **Current**: [One-line summary of active issue]
   - **Next**: [What needs to happen next, if anything]
   ```

   Skip clients with no active issues (status = Resolved/Closed with no pending work).

3. **End-of-day tasks**: Look for any of these indicators in STATUS.md files:

   - "EOD", "end of day", "by close of business", "COB"
   - "today", "due today"
   - Explicit dates matching today's date
   - "urgent", "ASAP" items

   Present either:

   - A bulleted list of tasks due today with client name
   - "No tasks due end-of-day." if nothing is due

## Output Format

```
# End-of-Day Status

## [Client 1]
...

## [Client 2]
...

---

## Due Today
- [ ] [Task] ([Client])
- [ ] [Task] ([Client])

*Or: "No tasks due end-of-day."*
```

Keep summaries brief - this is a quick status check, not a deep dive.
