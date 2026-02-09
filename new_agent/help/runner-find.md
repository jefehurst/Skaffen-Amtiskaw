# runner-find

Search Runner Technologies support portal.

## Usage

```bash
just runner-find "QUERY"
```

## Arguments

| Arg   | Description           |
| ----- | --------------------- |
| QUERY | Search terms (quoted) |

## Prerequisites

- Must be logged in: `just runner-login`
- Check status: `just runner-status`

## Examples

```bash
# Search for CLEAN_Address docs
just runner-find "CLEAN_Address configuration"

# Search for error messages
just runner-find "connection timeout"
```

## Related Recipes

| Recipe          | Purpose                |
| --------------- | ---------------------- |
| `runner-login`  | Authenticate to portal |
| `runner-status` | Check session status   |

## Notes

- Runner support has smaller knowledge base than Ellucian
- May need to contact support directly for complex issues
