tmux-capture: Read pane content

USAGE: just tmux-capture TARGET (visible) just tmux-capture-full TARGET [LINES] (with scrollback, default 1000)

TARGET: %N (pane ID), win.pane, etc. OUTPUT: raw pane text including prompts/output

EX: just tmux-capture %42 just tmux-capture-full %42 500 just tmux-capture %42 | grep "error"

RELATED: tmux-tail (last N), tmux-grep (search), tmux-exec (run+capture) FIND TARGET: just tmux-list-panes
