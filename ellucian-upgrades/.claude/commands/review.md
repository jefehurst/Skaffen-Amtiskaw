---
description: Security-focused code review
---

Review recent changes for security and correctness:

1. Run `git diff HEAD~1` (or staged changes if uncommitted)
2. Analyze for:

## Security Checklist

- [ ] Input validation and sanitization
- [ ] SQL/command injection risks
- [ ] XSS vulnerabilities
- [ ] Authentication/authorization logic
- [ ] Secrets or credentials in code
- [ ] Error messages leaking sensitive info

## Correctness Checklist

- [ ] Logic errors
- [ ] Edge cases handled
- [ ] Error handling present
- [ ] Resource cleanup (files, connections)

## Format Findings As

| Severity | File:Line | Issue | Suggested Fix |
| -------- | --------- | ----- | ------------- |

Focus on real bugs. Ignore style nitpicks.
