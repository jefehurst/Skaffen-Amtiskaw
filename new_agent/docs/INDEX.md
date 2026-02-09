# Documentation Index

This index documents vendor documentation that can be ingested into the project using `scripts/chunk-pdf.sh`.

______________________________________________________________________

## Available Documentation Sets

The following documentation sets have been ingested in previous SoS instances and can be re-ingested from original PDFs:

### Ellucian ODS Documentation

**Source**: Ellucian support portal PDFs **Ingestion method**: `scripts/chunk-pdf.sh` **Contents**:

- Installation, upgrade, and administration guides
- Troubleshooting guides
- Migration guides (Streams to MVIEWs)

### Runner CLEAN_Address Documentation

**Source**: Runner support portal (files.runneredq.com) **Ingestion method**: `scripts/chunk-pdf.sh` **Contents**:

- Installation checklists for Banner 8 and 9
- User guides
- Plugin deployment guides
- Troubleshooting articles

### Banner SSO Documentation

**Source**: Ellucian support portal + internal research **Contents**:

- Complete SSO setup procedure
- IdP-specific guides (Entra ID, Shibboleth)
- Troubleshooting checklists

______________________________________________________________________

## Re-ingestion Procedure

To ingest documentation from PDF:

1. Obtain original PDF from vendor support portal
2. Run: `./scripts/chunk-pdf.sh ~/Downloads/document.pdf docs/vendor/topic-name 20`
3. Review generated INDEX.md
4. Read chunks and add summaries to INDEX.md

The chunking script creates:

- `_toc.txt` - First 5 pages (usually table of contents)
- `_full-text.txt` - Complete extracted text for searching
- `chunk-NN-pX-Y.txt` - Individual chunks by page range
- `INDEX.md` - Template for documenting the content

______________________________________________________________________

## Directory Structure

When documentation is ingested, it follows this structure:

```
docs/
├── INDEX.md                    # This file
├── ellucian/                   # Ellucian product documentation
│   └── ods/                    # ODS documentation (chunked from PDFs)
├── runner/                     # Runner Technologies documentation
│   └── clean-address/          # CLEAN_Address documentation
└── banner-sso/                 # Banner SSO/SAML configuration
```
