tmux-list-panes: Show all panes with IDs

USAGE: just tmux-list-panes OUTPUT: session:win.pane %ID WxH command cwd

EX OUTPUT: main:0.0 %38 180x50 bash /home/user/project work:1.0 %42 120x40 vim /home/user/docs

USE %ID: just tmux-send %42 "cmd" RELATED: tmux-list-windows, tmux-context, tmux-pane-status
