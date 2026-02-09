# Ellucian Research Profile

This profile covers research tools and procedures for Ellucian products (Banner, Colleague, Ethos, ESM, etc.).

## Behavioral Corrections

### Article Naming Convention (CRITICAL - Repeated Error)

**Problem**: Incorrectly prefixing Ellucian article IDs with "KB" (e.g., "KB000511193")

**Correction**: Ellucian uses plain numeric IDs only. User-facing titles must read:

- ✅ "Ellucian Article 000511193: Banner DB Upgrade Issues"
- ❌ "KB000511193" or "Ellucian KB 000511193" or "KB Article..."

**Why This Matters**: This error has been corrected multiple times. The user explicitly stated: "We keep putting this
'KB' on things related to ellucian-support and as I've pointed out before that's not their nomenclature."

**Where This Applies**:

- Confluence page titles
- STATUS.md/SESSION_LOG.md references
- Any user-facing output mentioning Ellucian articles
- The `ellucian-support` CLI output formatting

## Product Notes

**EIS (Ellucian Identity Service)** aka Ellucian Ethos Identity:

- WSO2 Identity Server with Ellucian customization
- Implements CAS protocol
- Version visible in EIS Admin: Configure → Ellucian Ethos Identity
- On server: `$EIS_HOME/repository/components/default/configuration/org.wso2.carbon.server/carbon.xml`
- HTTP header `Server: WSO2 Carbon Server` confirms WSO2 but doesn't expose version

## Research Priority

Public web searches return very little useful information about enterprise vendor products. Always use this order:

1. **Internal docs** (`docs/ellucian/`) - Previously researched topics
2. **Logseq journals** - Past troubleshooting sessions
3. **Ellucian Support CLI** - Knowledge base, defects (requires MFA)
4. **Web search** - Last resort, usually unhelpful

## Ellucian Support CLI

### MFA Authentication Flow

The `ellucian-support` CLI requires Okta MFA. Sessions expire, so when searching:

1. **Ask the user for the MFA code first** before running the search command
2. Pass the MFA code via stdin to the login command:
   ```bash
   cd ./ellucian-support && echo "123456" | poetry run ellucian-support login -f
   ```
3. Then run the search command normally

Do NOT run the search command when the session is expired - it will fail waiting for interactive input.

### CLI Reference

```bash
# Search with filters
ellucian-support find "query" --source <source> -n <count>

# Sources: docs, kb, defect, release, idea, community
# Types: html, pdf, kb

# Examples
ellucian-support find "Banner SAML" --source kb -n 10
ellucian-support find "installation guide" --source docs --type pdf
ellucian-support find "error" -s kb -s defect   # multiple sources

# Fetch full article
ellucian-support fetch <article-url-or-sys-id>
```

### Publish to ITKB

**After fetching any article relevant to current work**, immediately publish a verbatim copy to Confluence ITKB:

1. Convert to markdown (preserve exact content - no summarizing or paraphrasing)
2. Search ITKB: `CQL: title ~ "000012345" AND space = ITKB`
3. Create page if not found (spaceId: `YOUR_SPACE_ID`)
4. Apply labels: `source:ellucian-support`, `product:<product>`, `type:<kb|defect|docs>`, `retrieved:<date>`
5. Add attribution header with article number, retrieval date, and applicable versions

**Note**: Ellucian uses plain numeric IDs (e.g., `000502999`), not "KB" prefixes. Title format: "Ellucian Article
XXXXXX: [Title]"

See CLAUDE.md "Knowledge Base (Confluence)" section for full details.

### Search Filters

| Option             | Use Case                                  |
| ------------------ | ----------------------------------------- |
| `--source docs`    | Official Ellucian documentation           |
| `--source kb`      | Knowledge base articles (troubleshooting) |
| `--source defect`  | Known bugs and defects                    |
| `--source release` | Release notes and version info            |
| `-n <count>`       | Number of results (default: 10)           |
| `--type pdf`       | Filter to PDF attachments                 |
| `--json`           | Output as JSON                            |

## Download Center CLI

The Download Center uses FlexNet Operations with separate SAML authentication through Okta. It shares the same Okta
session as Support Center but authenticates to FlexNet separately.

### Commands

```bash
# List all available products
ellucian-support download products

# Search for products by name
ellucian-support download products -q "ethos"
ellucian-support download products -q "banner"

# List files for a product (use line ID from products list)
ellucian-support download files "Ellucian-Ethos-Identity"

# Filter files by pattern (matches filename)
ellucian-support download files "Ellucian-Ethos-Identity" -p "5.10"
ellucian-support download files "Ellucian-Banner-General-Release" -p "9.20"

# Download files (dry run first)
ellucian-support download get "Ellucian-Ethos-Identity" -p "5.10" -n

# Download files to a directory
ellucian-support download get "Ellucian-Ethos-Identity" -p "baseline-5.10.0" -o ./downloads

# Download all 5.x versions
ellucian-support download get "Ellucian-Ethos-Identity" -p "5." -o ./ethos-5x
```

### Product Line IDs

Products are identified by "line ID" (hyphenated name), not display name:

| Display Name                       | Line ID                         |
| ---------------------------------- | ------------------------------- |
| Ellucian - Ellucian Ethos Identity | Ellucian-Ethos-Identity         |
| Ellucian - Banner General Release  | Ellucian-Banner-General-Release |

Use `download products` to discover available line IDs.

### Download Options

| Option       | Description                                   |
| ------------ | --------------------------------------------- |
| `-p PATTERN` | Filter files by pattern (substring match)     |
| `-o DIR`     | Output directory (default: current directory) |
| `-n`         | Dry run - show what would be downloaded       |
| `--json`     | Output file list as JSON                      |

## Documentation Output

Store researched vendor documentation in `docs/` with appropriate subdirectories:

- `docs/banner-sso/` - Banner SSO/SAML configuration
- `docs/esm/` - Ellucian Solution Manager
- `docs/ellucian/` - General Ellucian product docs

## Related Profiles

- **Banner Troubleshooting** (`profiles/banner-troubleshooting.md`) - Oracle/Banner-specific issues, SQL queries,
  upgrade procedures
