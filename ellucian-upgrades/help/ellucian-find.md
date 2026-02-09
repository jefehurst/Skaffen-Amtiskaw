# ellucian-find

Search Ellucian support portal for articles, defects, and documentation.

## Usage

```bash
just ellucian-find "QUERY" [OPTIONS]
```

## Arguments

| Arg   | Description                                    |
| ----- | ---------------------------------------------- |
| QUERY | Search terms (quoted string)                   |
| ARGS  | Additional CLI args passed to ellucian-support |

## Prerequisites

- Must be logged in: `just ellucian-login`
- Check status: `just ellucian-status`

## Examples

```bash
# Basic search
just ellucian-find "GUBVERS upgrade"

# Search with filters
just ellucian-find "INB session timeout" --type kb

# Search for defects
just ellucian-find "BPAM-12345"
```

## Common Options

| Option       | Description                       |
| ------------ | --------------------------------- |
| `--type kb`  | Filter to knowledge base articles |
| `--type def` | Filter to defect reports          |
| `--limit N`  | Max results to return             |

## Related Recipes

- `ellucian-fetch` - Fetch full article content
- `ellucian-login` - Authenticate to portal
- `ellucian-status` - Check session status

## Troubleshooting

**"Session expired"**: Run `just ellucian-login` and complete MFA.

**No results**: Try broader terms or check spelling. Ellucian search is literal.
