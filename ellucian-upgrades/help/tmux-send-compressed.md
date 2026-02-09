tmux-send: Execute command in another pane

USAGE: just tmux-send TARGET CMD TARGET: %N (pane ID), session:win.pane, win.pane, or relative (right/left) ACTION:
sends CMD + Enter

EX: just tmux-send %42 "npm run build" just tmux-send 1.0 "git status"

FIND TARGET: just tmux-list-panes RELATED: tmux-type (no Enter), tmux-capture (read), tmux-exec (send+capture)
