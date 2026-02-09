tmux-exec: Run command in pane, capture output (sync)

USAGE: just tmux-exec TARGET CMD TARGET: %N (pane ID) TIMEOUT: 60s

BEHAVIOR: Ctrl+C → send cmd+marker → poll → return stdout OUTPUT: command stdout only (filtered)

EX: just tmux-exec %42 "pwd" just tmux-exec %42 "git status"

CAVEATS: sends Ctrl+C first (interrupts running cmd), 60s timeout, shell prompt required RELATED: tmux-send
(fire-forget), tmux-capture (read only), tmux-wait-idle ERR: timeout → cmd slow or not at prompt; empty → cmd failed
