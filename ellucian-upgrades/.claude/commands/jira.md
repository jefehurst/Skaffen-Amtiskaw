---
description: Fetch and review all open tickets assigned to me
---

Fetch all open Jira tickets assigned to the current user and update client STATUS files.

## Process

### Step 1: Get Minimal Ticket List

Use `mcp__atlassian__searchJiraIssuesUsingJql` with minimal fields to avoid token overflow:

```
JQL: assignee = currentUser() AND status NOT IN (Done, Closed, Resolved) ORDER BY project, updated DESC
fields: ["key", "summary", "status", "priority", "project", "created"]
maxResults: 100
```

This returns only essential data - no descriptions, comments, or other heavy fields.

### Step 2: Group by Project

Parse results and group tickets by project key:

- Map Jira project keys to `clients/<name>/STATUS.md` directories
- Projects without a matching client directory → report but don't update

### Step 3: Update STATUS Files

For each client with a STATUS.md, update the "Open Jira Tickets" table.

**Do NOT fetch individual ticket details** unless explicitly asked. The search results contain everything needed for the
table.

## Output Format

Update each STATUS.md with:

```markdown
## Open Jira Tickets

| Key          | Summary                              | Status      | Priority |
| ------------ | ------------------------------------ | ----------- | -------- |
| PROJECT-123  | Ticket summary here                  | In Progress | Medium   |
```

Formatting rules:

- **Bold** tickets in "Blocked" status
- Mark tickets created in last 48 hours with **New** annotation below table
- Sort by ticket key (descending) within each project

## Token Efficiency

**Critical**: The initial search must NOT include description or other large fields. If the search response is
truncated:

1. Reduce maxResults
2. Run separate queries per project if needed
3. Never request fields you don't need

## IMPORTANT: Read-Only by Default

**Jira ticket updates send email notifications to all watchers and mentioned users.**

Do NOT:

- Add comments to tickets
- Change ticket status/transitions
- Edit ticket fields
- Create new tickets

These actions should only be taken when explicitly directed by the user.

This command is for **reading and reporting only** - updating local STATUS.md files does not notify anyone.
