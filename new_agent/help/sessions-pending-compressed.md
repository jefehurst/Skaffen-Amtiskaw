`just sessions-pending` - List new/updated sessions since last review.

Output: TSV `STATUS ID MTIME SIZE`. STATUS=NEW|UPDATED. Filters \<1KB sessions.

Compares `~/.claude/projects/<project-path>/*.jsonl` against `reflect/reviewed.tsv`.

Related: `sessions-summary` (counts), `sessions-mark` (mark reviewed), `analyze-sessions` (patterns).
