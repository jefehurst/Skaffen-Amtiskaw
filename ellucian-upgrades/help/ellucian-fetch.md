# ellucian-fetch

Fetch full content of an Ellucian support article by URL or sys_id.

## Usage

```bash
just ellucian-fetch ARTICLE
```

## Arguments

| Arg     | Description                                    |
| ------- | ---------------------------------------------- |
| ARTICLE | Full URL, article number, or ServiceNow sys_id |

## Prerequisites

- Must be logged in: `just ellucian-login`
- Check status: `just ellucian-status`

## Examples

```bash
# Fetch by article number
just ellucian-fetch 000502999

# Fetch by full URL
just ellucian-fetch "https://ellucian.service-now.com/client_portal?id=kb_article&sys_id=abc123"

# Fetch by sys_id
just ellucian-fetch abc123def456
```

## Output

Returns article content in markdown format including:

- Title and metadata
- Article body
- Attachments list (if any)

## Related Recipes

- `ellucian-find` - Search for articles
- `ellucian-login` - Authenticate to portal
- `ellucian-status` - Check session status

## Workflow

1. Search: `just ellucian-find "topic"`
2. Identify article from results
3. Fetch: `just ellucian-fetch ARTICLE_ID`
4. Publish to ITKB if relevant (see CLAUDE.md)

## Troubleshooting

**"Article not found"**: Verify the ID/URL. Try searching first.

**"Session expired"**: Run `just ellucian-login` and complete MFA.
