#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# start.sh - Launch Claude Code with project environment
#
# Works in both interactive and CI/headless modes. Use -p "prompt" for
# non-interactive execution.
#
# Options:
#   --tmux        Force tmux wrapper (default when not already in tmux)
#   --no-tmux     Skip tmux wrapper, run claude directly
#   -j, --join    Attach to existing sos tmux session (no new window)
#   -J, --join-independent
#                 Join existing session with independent window view
#                 (two terminals can look at different windows)
#   -r, --resume  Resume previous session (passed to claude)
#   -c            Continue most recent conversation
#   -p "..."      Headless/CI mode (implies --no-tmux)
#
# Positional args:
#   <name>        Optional: set tmux window name and invoke shortcut/client
#
# Shortcut resolution (when <name> provided):
#   1. shortcuts/<name>.md exists       -> use file contents as startup prompt
#   2. .claude/commands/<name>.md exists -> invoke "/<name>"
#   3. profiles/<name>.md exists        -> load that profile
#   4. clients/<name>/ exists           -> invoke "/client <name>"
#   5. Otherwise                        -> just set tmux window name
# =============================================================================

# Parse our flags (pass remaining args to claude)
USE_TMUX="auto" # auto | yes | no
JOIN_ONLY=false
JOIN_INDEPENDENT=false
HEADLESS=false
TMUX_NAME=""
CLAUDE_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tmux)
      USE_TMUX="yes"
      shift
      ;;
    --no-tmux)
      USE_TMUX="no"
      shift
      ;;
    -j | --join)
      JOIN_ONLY=true
      shift
      ;;
    -J | --join-independent)
      JOIN_INDEPENDENT=true
      shift
      ;;
    -r | --resume)
      # Pass through to claude
      CLAUDE_ARGS+=("$1")
      shift
      ;;
    -c)
      # Continue most recent - pass through to claude
      CLAUDE_ARGS+=("$1")
      shift
      ;;
    -p | --prompt)
      HEADLESS=true
      USE_TMUX="no" # Headless implies no tmux
      CLAUDE_ARGS+=("$1" "$2")
      shift 2
      ;;
    *)
      # First positional arg (not starting with -) becomes tmux name
      if [[ -z "$TMUX_NAME" && ! "$1" =~ ^- ]]; then
        TMUX_NAME="$1"
      else
        CLAUDE_ARGS+=("$1")
      fi
      shift
      ;;
  esac
done

# Require TTY for interactive mode, allow headless without
if [[ "$HEADLESS" == "false" && ! -t 0 ]]; then
  echo "ERROR: No TTY available for interactive mode." >&2
  echo "       Use -p \"prompt\" for headless/CI execution." >&2
  exit 1
fi

# Check for nix
if ! command -v nix &>/dev/null; then
  cat >&2 <<'EOF'

ERROR: nix not found in PATH.

Install Nix with:
  curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install

Then re-run this script.

EOF
  exit 1
fi

# Get script directory for relative paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# System prompt additions (persistent throughout session)
SYSTEM_PROMPT_FILE="$SCRIPT_DIR/config/system-prompt.txt"

# Ensure pre-commit hooks are installed
if [[ -d "$SCRIPT_DIR/.git" && ! -f "$SCRIPT_DIR/.git/hooks/pre-commit" ]]; then
  echo "Installing pre-commit hooks..." >&2
  nix develop "$SCRIPT_DIR" --command pre-commit install --install-hooks >/dev/null 2>&1 || true
fi

# Warn if local.env is missing (it gets loaded by flake shellHook)
if [[ ! -f "$SCRIPT_DIR/local.env" ]]; then
  if [[ "$HEADLESS" == "true" ]]; then
    echo "WARNING: local.env not found" >&2
  else
    cat >&2 <<'EOF'

╔══════════════════════════════════════════════════════════════════════════════╗
║  WARNING: local.env not found                                                ║
║                                                                              ║
║  Some features (Logseq, vendor support tools, etc.) may not work.            ║
║                                                                              ║
║  To set up:                                                                  ║
║    cp local.env.example local.env                                            ║
║    # Then edit local.env with your tokens                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

EOF
  fi
fi

# -----------------------------------------------------------------------------
# Determine tmux behavior
# -----------------------------------------------------------------------------
# Already in tmux or _SOS_IN_TMUX set: run claude directly
# Not in tmux + auto/yes: wrap in tmux and re-exec
# Not in tmux + no: run claude directly
SHOULD_WRAP_TMUX=false
if [[ -z "${TMUX:-}" && -z "${_SOS_IN_TMUX:-}" ]]; then
  if [[ "$USE_TMUX" == "auto" || "$USE_TMUX" == "yes" ]]; then
    SHOULD_WRAP_TMUX=true
  fi
fi

# -----------------------------------------------------------------------------
# Join-only mode: just attach to existing session
# -----------------------------------------------------------------------------
if [[ "$JOIN_ONLY" == "true" ]]; then
  TMUX_CONF="$SCRIPT_DIR/config/tmux/tmux.conf"
  TMUX_SOCKET="/tmp/sos-tmux.sock"

  if ! tmux -S "$TMUX_SOCKET" has-session -t sos 2>/dev/null; then
    echo "ERROR: No existing sos session to join." >&2
    echo "       Start a session first with: ./start.sh" >&2
    exit 1
  fi

  exec tmux -S "$TMUX_SOCKET" -f "$TMUX_CONF" attach-session -t sos
fi

# -----------------------------------------------------------------------------
# Join-independent mode: create grouped session for independent window view
# -----------------------------------------------------------------------------
if [[ "$JOIN_INDEPENDENT" == "true" ]]; then
  TMUX_CONF="$SCRIPT_DIR/config/tmux/tmux.conf"
  TMUX_SOCKET="/tmp/sos-tmux.sock"

  if ! tmux -S "$TMUX_SOCKET" has-session -t sos 2>/dev/null; then
    echo "ERROR: No existing sos session to join." >&2
    echo "       Start a session first with: ./start.sh" >&2
    exit 1
  fi

  # Create a grouped session that shares windows but has independent view
  # Session name includes PID to allow multiple independent joins
  GROUPED_SESSION="sos-$$"
  exec tmux -S "$TMUX_SOCKET" -f "$TMUX_CONF" new-session -t sos -s "$GROUPED_SESSION"
fi

# -----------------------------------------------------------------------------
# Launch
# -----------------------------------------------------------------------------
if [[ "$SHOULD_WRAP_TMUX" == "true" ]]; then
  # Launch in tmux session "sos" (creates or attaches)
  # Use /tmp to avoid polluting repo (Nix flakes can't handle socket files)
  TMUX_CONF="$SCRIPT_DIR/config/tmux/tmux.conf"
  TMUX_SOCKET="/tmp/sos-tmux.sock"

  echo "Starting tmux session 'sos' (socket: $TMUX_SOCKET)..." >&2
  # Use absolute path for re-exec
  SCRIPT_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"

  # Disable strict mode for tmux operations (interferes with terminal allocation)
  set +euxo pipefail

  # Check if session exists; if not, create it detached first
  if ! tmux -S "$TMUX_SOCKET" has-session -t sos 2>/dev/null; then
    # NEW SESSION: export state for re-exec, startup prompt will be used
    export _SOS_IN_TMUX=1
    export _SOS_TMUX_NAME="$TMUX_NAME"
    if [[ -n "$TMUX_NAME" ]]; then
      tmux -S "$TMUX_SOCKET" -f "$TMUX_CONF" new-session -d -s sos -n "$TMUX_NAME" "$SCRIPT_PATH" "${CLAUDE_ARGS[@]}"
    else
      tmux -S "$TMUX_SOCKET" -f "$TMUX_CONF" new-session -d -s sos "$SCRIPT_PATH" "${CLAUDE_ARGS[@]}"
    fi
  else
    # EXISTING SESSION: create new window, do NOT pass TMUX_NAME to avoid
    # re-injecting startup prompts. The user just wants a fresh Claude instance.
    export _SOS_IN_TMUX=1
    export _SOS_TMUX_NAME=""
    if [[ -n "$TMUX_NAME" ]]; then
      tmux -S "$TMUX_SOCKET" -f "$TMUX_CONF" new-window -t sos -n "$TMUX_NAME" "$SCRIPT_PATH" "${CLAUDE_ARGS[@]}"
    else
      tmux -S "$TMUX_SOCKET" -f "$TMUX_CONF" new-window -t sos "$SCRIPT_PATH" "${CLAUDE_ARGS[@]}"
    fi
  fi
  # Attach to session
  exec tmux -S "$TMUX_SOCKET" -f "$TMUX_CONF" attach-session -t sos
fi

# ---------------------------------------------------------------------------
# Direct launch (already in tmux, --no-tmux, or re-exec from tmux wrapper)
# ---------------------------------------------------------------------------

# Restore state from env if re-execing from tmux wrapper
if [[ -n "${_SOS_IN_TMUX:-}" ]]; then
  TMUX_NAME="${_SOS_TMUX_NAME:-}"
  unset _SOS_IN_TMUX _SOS_TMUX_NAME
  # Also remove from tmux's global environment so future windows don't inherit
  if [[ -n "${TMUX:-}" ]]; then
    tmux set-environment -gu _SOS_IN_TMUX 2>/dev/null || true
    tmux set-environment -gu _SOS_TMUX_NAME 2>/dev/null || true
  fi
fi

cd "$SCRIPT_DIR"

# Build startup prompt from name (if provided)
# Priority: shortcuts -> commands -> profiles -> clients
STARTUP_PROMPT=""
if [[ -n "$TMUX_NAME" ]]; then
  if [[ -f "$SCRIPT_DIR/shortcuts/$TMUX_NAME.md" ]]; then
    STARTUP_PROMPT="$(cat "$SCRIPT_DIR/shortcuts/$TMUX_NAME.md")"
  elif [[ -f "$SCRIPT_DIR/.claude/commands/$TMUX_NAME.md" ]]; then
    STARTUP_PROMPT="/$TMUX_NAME"
  elif [[ -f "$SCRIPT_DIR/profiles/$TMUX_NAME.md" ]]; then
    STARTUP_PROMPT="Load profiles/$TMUX_NAME.md"
  elif [[ -d "$SCRIPT_DIR/clients/$TMUX_NAME" ]]; then
    STARTUP_PROMPT="/client $TMUX_NAME"
  fi
fi

# Set tmux window name if provided and we're in tmux
if [[ -n "$TMUX_NAME" && -n "${TMUX:-}" ]]; then
  tmux rename-window "$TMUX_NAME"
fi

# Build claude command with system prompt if file exists
CLAUDE_CMD=(claude --permission-mode acceptEdits)
if [[ -f "$SYSTEM_PROMPT_FILE" ]]; then
  CLAUDE_CMD+=(--append-system-prompt "$(cat "$SYSTEM_PROMPT_FILE")")
fi
CLAUDE_CMD+=("${CLAUDE_ARGS[@]}")

# Add startup prompt as positional argument (not -p which is non-interactive)
if [[ -n "$STARTUP_PROMPT" ]]; then
  CLAUDE_CMD+=("$STARTUP_PROMPT")
fi

# Run claude in nix devshell (shellHook loads local.env)
nix develop "$SCRIPT_DIR" --impure --command bash -c 'echo "Launching SoS..." >&2; exec "$@"' -- "${CLAUDE_CMD[@]}"
EXIT_CODE=$?

if [[ "$HEADLESS" == "false" ]]; then
  cat >&2 <<'EOF'

────────────────────────────────────────────────────────────────────────────────
  Session ended. To resume:

    ./start.sh -c      # Continue most recent conversation
    ./start.sh -r      # Resume with session picker

  Or start fresh:

    ./start.sh         # New session
────────────────────────────────────────────────────────────────────────────────

EOF
fi

exit $EXIT_CODE
