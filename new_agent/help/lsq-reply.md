# lsq-reply

Add a new block as child or sibling of an existing block.

## Usage

```bash
# Add as child (nested under target)
just lsq-reply UUID CONTENT

# Add as sibling (same level as target)
just lsq-reply UUID CONTENT true
```

## Arguments

| Arg     | Description                          |
| ------- | ------------------------------------ |
| UUID    | Target block UUID                    |
| CONTENT | New block content (quoted)           |
| SIBLING | Any non-empty value = add as sibling |

## Examples

```bash
# Add child block (indented under target)
just lsq-reply "abc123" "This is a child block"

# Add sibling block (same level)
just lsq-reply "abc123" "This is a sibling" true

# Add task as child
just lsq-reply "abc123" "TODO New task"
```

## Child vs Sibling

```
- Target block (UUID: abc123)
  - Child block    ← just lsq-reply "abc123" "Child"
- Sibling block    ← just lsq-reply "abc123" "Sibling" true
```

## Related Recipes

| Recipe             | Purpose                   |
| ------------------ | ------------------------- |
| `lsq-blocks`       | Get block UUIDs           |
| `lsq-update`       | Modify existing block     |
| `lsq-remove`       | Delete a block            |
| `lsq-section-uuid` | Find section heading UUID |

## Common Workflow

1. Find target: `just lsq-blocks "Page" | jq '.[] | select(.content | contains("Target"))'`
2. Get UUID from result
3. Add reply: `just lsq-reply "uuid" "New content"`
