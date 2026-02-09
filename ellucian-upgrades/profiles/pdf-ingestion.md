# PDF Ingestion Profile

This profile covers procedures for ingesting large PDF documentation that exceeds context limits.

## Chunking Procedure

Use `scripts/chunk-pdf.sh` to split PDFs into manageable chunks:

```bash
./scripts/chunk-pdf.sh <input.pdf> <output-dir> [pages-per-chunk]

# Example:
./scripts/chunk-pdf.sh ~/Downloads/manual.pdf ./docs/product/manual 20
```

This creates:

- `_toc.txt` - Table of contents (first 5 pages)
- `_full-text.txt` - Complete text for grep/search
- `chunk-NN-pX-Y.txt` - Individual chunks of N pages each
- `INDEX.md` - Index file to track reading progress

## Reading and Summarizing

1. Read `_toc.txt` to understand document structure
2. Read chunks in order, updating `INDEX.md` with:
   - Chunk descriptions
   - Key concepts discovered
   - Important procedures
   - Configuration references
3. Use `grep` on `_full-text.txt` when searching for specific terms

## Documentation Locations

Researched documentation is stored in `docs/` with a root-level index at `docs/INDEX.md`.

| Product/Topic       | Location                       | Description                                        |
| ------------------- | ------------------------------ | -------------------------------------------------- |
| Documentation Index | [docs/INDEX.md](docs/INDEX.md) | Root index of all researched topics                |
| ESM Installation    | `docs/esm/installation/`       | Ellucian Solution Manager installation (103 pages) |

Always check `docs/INDEX.md` first when asked about a topic that may have been previously researched.
