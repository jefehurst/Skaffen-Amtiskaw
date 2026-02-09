# lsq-blocks

Get all blocks on a Logseq page.

## Usage

```bash
just lsq-blocks PAGE
```

## Arguments

| Arg  | Description                  |
| ---- | ---------------------------- |
| PAGE | Page name (case-insensitive) |

## Examples

```bash
# Get blocks from a page
just lsq-blocks "Project Notes"

# Get today's journal blocks
just lsq-blocks "Dec 17th, 2024"

# Get blocks from namespaced page
just lsq-blocks "work/meetings"
```

## Output

JSON array of blocks with:

- `uuid` - Block identifier
- `content` - Block text
- `children` - Nested blocks
- `properties` - Block properties

## Related Recipes

| Recipe       | Purpose                    |
| ------------ | -------------------------- |
| `lsq-find`   | Search blocks with filters |
| `lsq-update` | Modify a block             |
| `lsq-reply`  | Add child/sibling block    |
| `lsq-query`  | Custom Datalog query       |

## Notes

- Page names are case-insensitive
- Journal pages use date format: "Dec 17th, 2024"
- Namespaced pages use forward slash: "namespace/page"
