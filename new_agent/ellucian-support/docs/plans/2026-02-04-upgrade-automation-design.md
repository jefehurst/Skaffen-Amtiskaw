# Ellucian Banner Upgrade Documentation Automation

## Problem Statement

Creating quarterly upgrade documentation for Ellucian Banner releases is a time-intensive manual process:

- **25-50 releases per quarter** across multiple Banner modules
- **15 clients** requiring customized documentation based on their ESM state
- **Manual data entry** from Ellucian Customer Support portal to Confluence
- **Repetitive formatting** of defect/enhancement tables with consistent structure

Current workflow involves logging into the support site, reviewing each release, copying information, and creating detail pages - then repeating for each client with client-specific customizations.

## Solution Overview

A semi-automatic workflow with three phases:

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Data Collection   │────▶│ Client Customization│────▶│  Review & Publish   │
│                     │     │                     │     │                     │
│ - Search releases   │     │ - Load ESM state    │     │ - Human review      │
│ - Fetch details     │     │ - Filter relevance  │     │ - Add notes         │
│ - Get defects/enh   │     │ - Apply priorities  │     │ - Publish to Confl  │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

## Architecture

### Phase 1: Data Collection

Automated fetching from Ellucian Customer Support (ServiceNow-based).

**Authentication Flow:**
```
Okta IDX API
    │
    ├─ /idp/idx/introspect (get state handle)
    ├─ /idp/idx/identify (username)
    ├─ /idp/idx/challenge (password)
    ├─ /idp/idx/challenge (select TOTP authenticator)
    ├─ /idp/idx/challenge/answer (MFA code)
    └─ Follow redirects → session cookies
```

**Data Fetching:**

| Data              | API Endpoint                          | Method    |
|-------------------|---------------------------------------|-----------|
| Search releases   | Coveo Search API                      | POST      |
| Release details   | `/api/now/table/ellucian_product_release/{sys_id}` | GET |
| Related item IDs  | `/api/now/sp/page?id=standard_ticket` | GET       |
| Defect details    | `/api/now/table/ellucian_product_defect/{sys_id}` | GET |
| Enhancement details | `/api/now/table/ellucian_product_enhancement/{sys_id}` | GET |

**Note:** Query-based table API calls return 403; individual GETs work.

### Phase 2: Client Customization

Load client state from ESM and filter/prioritize releases.

**Inputs:**
- Release data from Phase 1
- Client's current module versions from ESM
- Client-specific exclusion rules

**Outputs:**
- Filtered release list (only applicable to client's versions)
- Priority assignments based on defect severity
- Pre-populated testing notes template

### Phase 3: Review & Publish

Human-in-the-loop review with Confluence publishing.

**Human Review Points:**
- Prioritization adjustments
- Client-specific notes and context
- Exclusions (not applicable, already addressed, etc.)
- Testing notes customization

**Publishing:**
- Generate Confluence page from template
- Create baseline table with release summary
- Create detail pages for defects/enhancements

## Data Models

### Release

```python
@dataclass
class Release:
    sys_id: str
    number: str              # e.g., "PR00039101"
    short_description: str   # e.g., "BA FIN AID 8.51.1.1"
    date_released: str       # e.g., "2025-02-06"
    product_line: str        # e.g., "Banner - Financial Aid"
    version: str             # e.g., "8.51.1.1"
    defect_ids: list[str]
    enhancement_ids: list[str]
```

### Defect

```python
@dataclass
class Defect:
    sys_id: str
    number: str              # e.g., "PD0020242"
    summary: str             # Brief description
    description: str         # Full issue details
    resolution: str          # How it was fixed
    client_impact: str       # Impact description
    object_process: str      # e.g., "roksapr1.sql"
    patch_number: str        # e.g., "pcr-0020242_res8510101"
    product_hierarchy: str   # e.g., "Banner - Financial Aid"
```

### Enhancement

```python
@dataclass
class Enhancement:
    sys_id: str
    number: str              # e.g., "PE0005812"
    summary: str             # Brief description
    description: str         # Full details
    business_purpose: str    # Why it was added
    product_hierarchy: str
```

## Output Format

### Quarterly Summary Table

| Module | Latest Version | Release Date | Defect/Enhancement/Regulatory | Dependencies |
|--------|---------------|--------------|-------------------------------|--------------|
| Banner Financial Aid | 8.51.1.1 | 2025-02-06 | 3D / 1E | Banner General 9.x |

### Defects Detail Table

| Module/Version | Change Request ID | Details | Testing Notes |
|----------------|-------------------|---------|---------------|
| Financial Aid 8.51.1.1 | PD0020242 | ROPSAPR aborts with numeric precision error when calculating SAP values exceeding column decimal places | Verify ROPSAPR completes without ORA-06502 errors |

### Enhancements Detail Table

| Module/Version | Change Request ID | Details | Testing Notes |
|----------------|-------------------|---------|---------------|
| Financial Aid 8.51.1.1 | PE0005812 | Deliver scripts to create seed data for RCPCA26 | Run seed data scripts and verify RCPCA26 population |

## Implementation Components

### ellucian-support CLI

Already implemented:
- `ellucian-support login` - Okta authentication with TOTP MFA
- Session persistence with cookie storage

To implement:
- `ellucian-support releases search --product "Banner" --after 2024-10-01`
- `ellucian-support releases show <sys_id> --with-defects --with-enhancements`
- `ellucian-support releases export --format json|csv|confluence`

### esm-cli (Future)

- `esm status <client>` - Get client's current module versions
- `esm compare <client> <release>` - Check if release applies to client

### Automation Workflow

```bash
# 1. Fetch all releases for the quarter
ellucian-support releases search \
    --product "Banner" \
    --after 2024-10-01 \
    --before 2025-01-01 \
    --output releases-q4-2024.json

# 2. Enrich with defects/enhancements
ellucian-support releases enrich \
    --input releases-q4-2024.json \
    --output releases-q4-2024-enriched.json

# 3. For each client, filter and customize
for client in client1 client2 ...; do
    esm compare $client releases-q4-2024-enriched.json \
        --output $client-upgrades.json
done

# 4. Generate Confluence pages (with human review)
ellucian-support publish \
    --input client1-upgrades.json \
    --template quarterly-upgrade \
    --confluence-space UPGRADES \
    --review  # Opens for human review before publishing
```

## API Details Discovered

### Coveo Search API

```python
COVEO_URL = "https://platform.cloud.coveo.com/rest/search/v2"
COVEO_ORG = "elluciancommunityproduction..."
COVEO_TOKEN = "xx..."  # From page source

params = {
    "organizationId": COVEO_ORG,
    "q": "Banner",
    "numberOfResults": 50,
    "fieldsToInclude": ["ellucian_product_line", "date_released", ...]
}
```

Response includes `raw` field with rich metadata:
- `ellucian_product_line`, `ellucian_product_name`
- `date_released`, `ellucian_product_version`
- `sys_id` for linking to Table API

### ServiceNow SP Page API

The related defects/enhancements are embedded in widget data:

```python
# Navigate to Standard Ticket Tab widget
containers = data['result']['containers']
# Find widget with name == 'Standard Ticket Tab'
# Extract tabs → widget → data → widget → options → filter
# filter format: "sys_idINabc,def,ghi"
```

### ServiceNow Table API

Direct GET by sys_id works:
```
GET /api/now/table/ellucian_product_defect/{sys_id}
```

Query-based access returns 403:
```
GET /api/now/table/ellucian_product_defect?sysparm_query=sys_idINabc,def
```

## Security Considerations

- Credentials stored in `local.env` (gitignored)
- Session cookies persisted locally with appropriate permissions
- No credentials in code or logs
- TOTP MFA required for each login session

## Next Steps

1. **Implement release search command** in ellucian-support CLI
2. **Implement release enrichment** (fetch defects/enhancements)
3. **Build ESM integration** for client version tracking
4. **Create Confluence templates** matching existing documentation format
5. **Build review interface** for human-in-the-loop customization
