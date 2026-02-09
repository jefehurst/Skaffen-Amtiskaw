lsq-reply: Add child or sibling block

USAGE: just lsq-reply UUID CONTENT [SIBLING] UUID: target block CONTENT: new block text SIBLING: any value → add as
sibling (default: child)

EX: just lsq-reply "abc123" "Child block" just lsq-reply "abc123" "Sibling" true

STRUCTURE:

- Target (abc123)
  - Child ← no SIBLING arg
- Sibling ← with SIBLING arg

GET UUID: just lsq-blocks "Page" | jq '.[].uuid' RELATED: lsq-blocks, lsq-update, lsq-remove, lsq-section-uuid
