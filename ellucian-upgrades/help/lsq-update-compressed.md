lsq-update: Modify block content by UUID

USAGE: just lsq-update UUID CONTENT UUID: from lsq-blocks, lsq-find, or lsq-query CONTENT: new block text (quoted),
overwrites entirely

EX: just lsq-update "abc123-def456" "Updated text" just lsq-update "abc123-def456" "DONE Task"

GET UUID: just lsq-blocks "Page" | jq '.[].uuid' RELATED: lsq-blocks, lsq-reply (add), lsq-remove, lsq-bulk-update
CAUTION: overwrites entire block, no CLI undo
