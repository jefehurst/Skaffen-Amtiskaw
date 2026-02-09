# lsq-update

Update a Logseq block's content by UUID.

## Usage

```bash
just lsq-update UUID CONTENT
```

## Arguments

| Arg     | Description                            |
| ------- | -------------------------------------- |
| UUID    | Block UUID (from lsq-blocks/lsq-query) |
| CONTENT | New block content (quoted)             |

## Examples

```bash
# Update a block
just lsq-update "abc123-def456" "Updated content here"

# Mark task as done
just lsq-update "abc123-def456" "DONE Task description"

# Add properties
just lsq-update "abc123-def456" "Block text
property:: value"
```

## Getting UUIDs

```bash
# From page blocks
just lsq-blocks "Page Name" | jq '.[].uuid'

# From search
just lsq-find "Page Name" --content "search term"

# From query
just lsq-query "[:find ?uuid :where [?b :block/uuid ?uuid] ...]"
```

## Related Recipes

| Recipe            | Purpose                       |
| ----------------- | ----------------------------- |
| `lsq-blocks`      | Get blocks with UUIDs         |
| `lsq-reply`       | Add new block (child/sibling) |
| `lsq-remove`      | Delete a block                |
| `lsq-bulk-update` | Update multiple blocks        |

## Caution

- Overwrites entire block content
- No undo from CLI (Logseq has undo in app)
- Verify UUID before updating
