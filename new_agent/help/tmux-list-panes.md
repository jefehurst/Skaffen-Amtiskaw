# tmux-list-panes

List all tmux panes across all sessions with their IDs and details.

## Usage

```bash
just tmux-list-panes
```

## Output Format

```
session:window.pane  pane_id  WxH  command  cwd
```

Example:

```
main:0.0  %38  180x50  bash  /home/user/project
main:0.1  %39  180x25  node  /home/user/project
work:1.0  %42  120x40  vim   /home/user/docs
```

## Column Description

| Column  | Description                  |
| ------- | ---------------------------- |
| target  | Session:window.pane format   |
| pane_id | Unique pane ID (`%N` format) |
| size    | Width x Height in characters |
| command | Currently running command    |
| cwd     | Current working directory    |

## Using Pane IDs

The `%N` pane ID is the most reliable target for other tmux recipes:

```bash
just tmux-send %42 "command"
just tmux-capture %42
just tmux-exec %42 "pwd"
```

## Related Recipes

| Recipe              | Purpose                 |
| ------------------- | ----------------------- |
| `tmux-list-windows` | List windows in session |
| `tmux-context`      | Current pane details    |
| `tmux-pane-status`  | Check if pane is idle   |
