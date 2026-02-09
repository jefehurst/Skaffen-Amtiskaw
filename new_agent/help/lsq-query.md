# lsq-query

Run a Datalog query against Logseq's database.

## Usage

```bash
just lsq-query "QUERY"
```

## Arguments

| Arg   | Description                   |
| ----- | ----------------------------- |
| QUERY | Datalog query string (quoted) |

## Examples

```bash
# Find all blocks with TODO marker
just lsq-query "[:find (pull ?b [*]) :where [?b :block/marker \"TODO\"]]"

# Find blocks on specific page
just lsq-query "[:find (pull ?b [*]) :where [?b :block/page ?p] [?p :block/name \"journal\"]]"

# Count blocks
just lsq-query "[:find (count ?b) :where [?b :block/uuid]]"
```

## Query Syntax

Logseq uses Datascript (Datalog for JS). Key patterns:

```clojure
[:find ?variable      ; What to return
 :where               ; Conditions
 [?b :block/content ?c]  ; Pattern: entity attr value
 [?b :block/page ?p]]    ; Join on shared ?b
```

## Common Attributes

| Attribute          | Description           |
| ------------------ | --------------------- |
| `:block/content`   | Block text            |
| `:block/uuid`      | Block unique ID       |
| `:block/page`      | Page entity reference |
| `:block/marker`    | TODO/DOING/DONE etc.  |
| `:block/scheduled` | Scheduled date        |
| `:block/deadline`  | Deadline date         |
| `:block/name`      | Page name (lowercase) |

## Related Recipes

| Recipe       | Purpose                    |
| ------------ | -------------------------- |
| `lsq-blocks` | Get all blocks on a page   |
| `lsq-find`   | Search blocks with filters |
| `lsq-recent` | Recently modified blocks   |

## Notes

- Queries run against Logseq's in-memory database
- Requires Logseq HTTP API enabled
- Complex queries may be slow on large graphs
