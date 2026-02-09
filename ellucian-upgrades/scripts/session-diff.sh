#!/usr/bin/env bash
# session-diff.sh - Find new or updated session logs
#
# Compares current sessions against reflect/reviewed.tsv
# Outputs only sessions that are new or modified since last review
#
# Usage:
#   ./session-diff.sh              # List new/updated sessions
#   ./session-diff.sh --mark ID    # Mark session as reviewed
#   ./session-diff.sh --summary    # Just counts

set -euo pipefail

# Auto-detect session directory from project path
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_SLUG="$(echo "$PROJECT_DIR" | sed 's|^/||; s|/|-|g')"
SESSIONS_DIR="${HOME}/.claude/projects/-${PROJECT_SLUG}"
REVIEWED_FILE="${SCRIPT_DIR:-$(dirname "$0")/../reflect}/reviewed.tsv"

# Handle relative path
if [[ ! -f "$REVIEWED_FILE" ]]; then
  REVIEWED_FILE="$(cd "$(dirname "$0")/.." && pwd)/reflect/reviewed.tsv"
fi

# Ensure reviewed file exists
if [[ ! -f "$REVIEWED_FILE" ]]; then
  echo "# Session ID  Last Modified   Review Date Findings Count" >"$REVIEWED_FILE"
fi

get_reviewed_sessions() {
  grep -v '^#' "$REVIEWED_FILE" 2>/dev/null | cut -f1 | sort
}

get_reviewed_mtime() {
  local session_id="$1"
  grep "^${session_id}    " "$REVIEWED_FILE" 2>/dev/null | cut -f2 || echo ""
}

get_current_sessions() {
  # Get session files with their modification times
  local id mtime mtime_iso size
  for f in "$SESSIONS_DIR"/*.jsonl; do
    [[ -f "$f" ]] || continue
    id=$(basename "$f" .jsonl)
    mtime=$(stat -c '%Y' "$f" 2>/dev/null || stat -f '%m' "$f" 2>/dev/null)
    mtime_iso=$(date -d "@$mtime" '+%Y-%m-%dT%H:%M' 2>/dev/null || date -r "$mtime" '+%Y-%m-%dT%H:%M' 2>/dev/null)
    size=$(stat -c '%s' "$f" 2>/dev/null || stat -f '%z' "$f" 2>/dev/null)
    printf '%s\t%s\t%s\n' "$id" "$mtime_iso" "$size"
  done
}

list_new_or_updated() {
  local reviewed new_count updated_count reviewed_mtime
  reviewed=$(get_reviewed_sessions)
  new_count=0
  updated_count=0

  while IFS=$'\t' read -r id mtime size; do
    [[ -z "$id" ]] && continue

    # Skip tiny sessions (likely just metadata)
    [[ "$size" -lt 1000 ]] && continue

    reviewed_mtime=$(get_reviewed_mtime "$id")

    if [[ -z "$reviewed_mtime" ]]; then
      printf 'NEW\t%s\t%s\t%s\n' "$id" "$mtime" "$size"
      ((new_count++)) || true
    elif [[ "$mtime" > "$reviewed_mtime" ]]; then
      printf 'UPDATED\t%s\t%s\t%s\n' "$id" "$mtime" "$size"
      ((updated_count++)) || true
    fi
  done < <(get_current_sessions)

  if [[ "${1:-}" == "--summary" ]]; then
    echo "---"
    echo "New: $new_count, Updated: $updated_count"
  fi
}

mark_reviewed() {
  local session_id="$1"
  local findings="${2:-0}"
  local today mtime mtime_iso session_file

  today=$(date '+%Y-%m-%d')
  session_file="$SESSIONS_DIR/${session_id}.jsonl"

  if [[ ! -f "$session_file" ]]; then
    echo "Session not found: $session_id" >&2
    exit 1
  fi

  mtime=$(stat -c '%Y' "$session_file" 2>/dev/null || stat -f '%m' "$session_file" 2>/dev/null)
  mtime_iso=$(date -d "@$mtime" '+%Y-%m-%dT%H:%M' 2>/dev/null || date -r "$mtime" '+%Y-%m-%dT%H:%M' 2>/dev/null)

  # Remove old entry if exists
  if grep -q "^${session_id}  " "$REVIEWED_FILE" 2>/dev/null; then
    grep -v "^${session_id} " "$REVIEWED_FILE" >"${REVIEWED_FILE}.tmp"
    mv "${REVIEWED_FILE}.tmp" "$REVIEWED_FILE"
  fi

  # Add new entry
  printf '%s\t%s\t%s\t%s\n' "$session_id" "$mtime_iso" "$today" "$findings" >>"$REVIEWED_FILE"
  echo "Marked $session_id as reviewed"
}

show_summary() {
  local total reviewed pending
  total=$(find "$SESSIONS_DIR" -maxdepth 1 -name '*.jsonl' 2>/dev/null | wc -l)
  reviewed=$(grep -cv '^#' "$REVIEWED_FILE" 2>/dev/null || echo 0)
  pending=$(list_new_or_updated 2>/dev/null | wc -l)

  echo "Sessions: $total total, $reviewed reviewed, $pending pending"
}

case "${1:-}" in
  --mark)
    mark_reviewed "${2:-}" "${3:-0}"
    ;;
  --summary)
    show_summary
    ;;
  --help | -h)
    echo "Usage: session-diff.sh [--mark ID [FINDINGS]] [--summary]"
    echo ""
    echo "  (no args)     List new/updated sessions (TSV: STATUS ID MTIME SIZE)"
    echo "  --mark ID N   Mark session as reviewed with N findings"
    echo "  --summary     Show counts only"
    ;;
  *)
    list_new_or_updated
    ;;
esac
