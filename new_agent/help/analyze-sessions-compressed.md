`just analyze-sessions` - Find correction patterns in session logs.

Variants: `analyze-sessions-json` (JSON), `analyze-sessions-save` (to file).

Finds: corrections ("no", "wrong", "instead"), instructions ("always", "never", "from now on"), frustration signals.

Output: Markdown report grouped by pattern type and frequency.

Script: `scripts/analyze_sessions.py`. Sessions: `~/.claude/projects/<project-path>/*.jsonl`.

Related: `sessions-pending`, `sessions-mark`, `/reflect` command.
