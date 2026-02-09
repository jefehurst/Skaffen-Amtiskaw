#!/usr/bin/env bash
set -euo pipefail

# chunk-pdf.sh - Extract and chunk PDF documentation for AI ingestion
#
# Usage:
#   ./chunk-pdf.sh <input.pdf> <output-dir> [pages-per-chunk]
#
# This script:
# 1. Extracts text from PDF using pdftotext
# 2. Splits into chunks of N pages (default: 20)
# 3. Creates an index of all chunks
#
# The chunks are sized to be readable by Claude without context overflow.

INPUT="${1:-}"
OUTDIR="${2:-}"
PAGES_PER_CHUNK="${3:-20}"

if [ -z "$INPUT" ] || [ -z "$OUTDIR" ]; then
  echo "Usage: $0 <input.pdf> <output-dir> [pages-per-chunk]"
  echo ""
  echo "Example:"
  echo "  $0 ~/Downloads/manual.pdf ./docs/manual-chunks 25"
  exit 1
fi

if [ ! -f "$INPUT" ]; then
  echo "Error: Input file not found: $INPUT"
  exit 1
fi

# Check for pdftotext
if ! command -v pdftotext &>/dev/null; then
  echo "Error: pdftotext not found. Install poppler-utils."
  exit 1
fi

if ! command -v pdfinfo &>/dev/null; then
  echo "Error: pdfinfo not found. Install poppler-utils."
  exit 1
fi

mkdir -p "$OUTDIR"

# Get PDF info
BASENAME=$(basename "$INPUT" .pdf)
TOTAL_PAGES=$(pdfinfo "$INPUT" | grep "^Pages:" | awk '{print $2}')
TITLE=$(pdfinfo "$INPUT" | grep "^Title:" | cut -d: -f2- | xargs)

echo "Processing: $INPUT"
echo "Title: ${TITLE:-$BASENAME}"
echo "Total pages: $TOTAL_PAGES"
echo "Pages per chunk: $PAGES_PER_CHUNK"
echo "Output directory: $OUTDIR"
echo ""

# Extract full text for reference
echo "Extracting full text..."
pdftotext "$INPUT" "$OUTDIR/_full-text.txt"

# Extract TOC (first 5 pages usually contain it)
echo "Extracting table of contents..."
pdftotext -f 1 -l 5 "$INPUT" "$OUTDIR/_toc.txt"

# Calculate number of chunks
NUM_CHUNKS=$(((TOTAL_PAGES + PAGES_PER_CHUNK - 1) / PAGES_PER_CHUNK))

echo "Creating $NUM_CHUNKS chunks..."

# Create chunks
for ((i = 0; i < NUM_CHUNKS; i++)); do
  START_PAGE=$((i * PAGES_PER_CHUNK + 1))
  END_PAGE=$(((i + 1) * PAGES_PER_CHUNK))

  if [ "$END_PAGE" -gt "$TOTAL_PAGES" ]; then
    END_PAGE=$TOTAL_PAGES
  fi

  CHUNK_NUM=$(printf "%02d" $((i + 1)))
  CHUNK_FILE="chunk-${CHUNK_NUM}-p${START_PAGE}-${END_PAGE}.txt"

  pdftotext -f "$START_PAGE" -l "$END_PAGE" "$INPUT" "$OUTDIR/$CHUNK_FILE"

  LINES=$(wc -l <"$OUTDIR/$CHUNK_FILE")
  echo "  Created $CHUNK_FILE ($LINES lines)"
done

# Create index file
cat >"$OUTDIR/INDEX.md" <<EOF
# ${TITLE:-$BASENAME}

**Source**: $(basename "$INPUT")
**Total Pages**: $TOTAL_PAGES
**Chunks**: $NUM_CHUNKS (${PAGES_PER_CHUNK} pages each)
**Generated**: $(date -Iseconds)

## Files

| File                  | Pages | Description     |
|-----------------------|-------|-----------------|
| _toc.txt              | 1-5   | Table of contents |
| _full-text.txt        | all   | Complete text (for searching) |
EOF

for ((i = 0; i < NUM_CHUNKS; i++)); do
  START_PAGE=$((i * PAGES_PER_CHUNK + 1))
  END_PAGE=$(((i + 1) * PAGES_PER_CHUNK))
  if [ "$END_PAGE" -gt "$TOTAL_PAGES" ]; then
    END_PAGE=$TOTAL_PAGES
  fi
  CHUNK_NUM=$(printf "%02d" $((i + 1)))
  printf "| chunk-%s-p%d-%d.txt | %d-%d | (add description) |\n" \
    "$CHUNK_NUM" "$START_PAGE" "$END_PAGE" "$START_PAGE" "$END_PAGE" >>"$OUTDIR/INDEX.md"
done

cat >>"$OUTDIR/INDEX.md" <<'EOF'

## Reading Procedure

To ingest this documentation:

1. Read `_toc.txt` first to understand structure
2. Read chunks in order, summarizing key points
3. Use `_full-text.txt` for grep/search when looking for specific terms

## Summary

(Add summary after reading chunks)

## Key Concepts

(Add key concepts after reading chunks)

## Quick Reference

(Add frequently-needed info after reading chunks)
EOF

echo ""
echo "Done! Created:"
ls -lh "$OUTDIR"
echo ""
echo "Next steps:"
echo "1. Read $OUTDIR/INDEX.md"
echo "2. Read $OUTDIR/_toc.txt to understand structure"
echo "3. Read chunks in order, updating INDEX.md with summaries"
