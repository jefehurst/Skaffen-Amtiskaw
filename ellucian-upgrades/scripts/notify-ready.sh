#!/usr/bin/env bash
# notify-ready.sh - Signal Claude's state to tmux tab
# Usage: notify-ready.sh [ready|attention|thinking|clear]
#   ready     - Green bg: Claude finished, waiting for input
#   attention - Orange bg: Permission prompt needs action
#   thinking  - Cyan italic: Extended thinking mode (manual use)
#   clear     - Reset to default style
#
# Silently does nothing if not in tmux

[[ -z "${TMUX:-}" ]] && exit 0

WINDOW=$(tmux display-message -p '#{window_index}' 2>/dev/null) || exit 0

case "${1:-ready}" in
  attention)
    # Orange background - needs user action (permission prompt)
    tmux set-window-option -t ":$WINDOW" window-status-style "bg=#ffa066,fg=#1f1f28,bold" 2>/dev/null
    tmux set-window-option -t ":$WINDOW" window-status-current-style "bg=#ffa066,fg=#1f1f28,bold" 2>/dev/null
    ;;
  thinking)
    # Dim italic - Claude is processing (subtle, no action needed)
    # NOTE: Not enabled by default - use for manual/extended thinking mode
    tmux set-window-option -t ":$WINDOW" window-status-style "fg=#7fb4ca,italics" 2>/dev/null
    tmux set-window-option -t ":$WINDOW" window-status-current-style "fg=#7fb4ca,italics" 2>/dev/null
    ;;
  clear)
    # Reset to default style
    tmux set-window-option -t ":$WINDOW" window-status-style default 2>/dev/null
    tmux set-window-option -t ":$WINDOW" window-status-current-style default 2>/dev/null
    ;;
  *)
    # Green background with dark text - readable on both focused and unfocused
    tmux set-window-option -t ":$WINDOW" window-status-style "bg=#98bb6c,fg=#1f1f28" 2>/dev/null
    tmux set-window-option -t ":$WINDOW" window-status-current-style "bg=#98bb6c,fg=#1f1f28" 2>/dev/null
    ;;
esac

exit 0
