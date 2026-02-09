# Runner Technologies Profile

This profile covers research tools and procedures for Runner Technologies products (CLEAN_Address, etc.).

## Research Priority

1. **Internal docs** (`docs/runner/`) - Previously researched topics
2. **Logseq journals** - Past troubleshooting sessions
3. **Runner Support CLI** - Support center articles
4. **Web search** - Last resort, usually limited results

## Runner Support CLI

### CLI Reference

```bash
# Search articles
runner-support search "query"

# Examples
runner-support search "CLEAN_Address configuration"
runner-support search "installation"

# Check login status
runner-support status

# Login (if needed)
runner-support login
```

### Research Priority Order

1. **First**: Use the `runner-support` CLI to search Runner's support center
2. **Second**: Web search for community discussions (usually limited)

### Publish to ITKB

**After fetching any article relevant to current work**, immediately publish a verbatim copy to Confluence ITKB:

1. Convert to markdown (preserve exact content - no summarizing or paraphrasing)
2. Search ITKB first to check if article exists
3. Create page if not found (spaceId: `YOUR_SPACE_ID`)
4. Apply labels: `source:runner-support`, `product:clean-address`, `type:<article-type>`, `retrieved:<date>`
5. Add attribution header with article ID, retrieval date, and applicable versions

See CLAUDE.md "Knowledge Base (Confluence)" section for full details.

## Documentation Output

Store researched vendor documentation in:

- `docs/runner/` - Runner Technologies product docs
