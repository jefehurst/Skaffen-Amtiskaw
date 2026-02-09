# Commit Mode

Make atomic commits until the working tree is clean.

## Process

1. Run `git status` to see all changes
2. Group related changes into logical commits
3. For each group:
   - Stage the related files
   - Write a concise commit message (what and why, not how)
   - Commit
4. Repeat until working tree is clean

## Commit Guidelines

**Atomic commits**: Each commit should be one logical change that could be reverted independently.

**Good groupings**:

- New feature: all files for that feature
- Bug fix: the fix + any related test
- Refactor: related structural changes
- Config: related configuration changes
- Docs: documentation updates

**Bad groupings**:

- Mixing unrelated changes
- "WIP" or "misc fixes"
- Combining feature + unrelated cleanup

**Message format**:

```
Short summary (imperative mood, <50 chars)

Optional body explaining why, not what.
The diff shows what changed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

## Safety

- Review `git diff --staged` before each commit
- Never commit secrets (.env, credentials, tokens)
- Never force push or amend commits not authored by you
- If pre-commit hooks modify files, amend only if safe (check authorship first)

## Example Session

```bash
$ git status
M  profiles/ellucian.md
M  profiles/banner-troubleshooting.md
A  scripts/session-diff.sh
A  reflect/LOG.md
M  justfile
```

Logical groups:

1. Profile updates (ellucian.md, banner-troubleshooting.md)
2. Session analysis tooling (session-diff.sh, LOG.md, justfile changes)

Two commits, not one.

## Begin

Run `git status` and `git diff` to see current changes, then create atomic commits.
