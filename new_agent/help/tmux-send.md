# tmux-send

Send a command to another tmux pane and execute it (presses Enter).

## Usage

```bash
just tmux-send TARGET CMD
```

## Arguments

| Arg    | Description                                   |
| ------ | --------------------------------------------- |
| TARGET | Pane identifier (e.g., `%42`, `1.0`, `right`) |
| CMD    | Command string to execute                     |

## Target Formats

| Format          | Example    | Meaning                          |
| --------------- | ---------- | -------------------------------- |
| `%N`            | `%42`      | Pane ID (most reliable)          |
| `session:win.p` | `main:1.0` | Session:window.pane              |
| `win.pane`      | `1.0`      | Window.pane in current session   |
| Relative        | `right`    | Relative to current (left/right) |

## Examples

```bash
# Send to pane %42
just tmux-send %42 "npm run build"

# Send to window 1, pane 0
just tmux-send 1.0 "git status"

# Send to pane to the right
just tmux-send right "echo hello"
```

## Related Recipes

| Recipe            | Purpose                          |
| ----------------- | -------------------------------- |
| `tmux-type`       | Type text WITHOUT pressing Enter |
| `tmux-capture`    | Read pane output                 |
| `tmux-exec`       | Send command and capture output  |
| `tmux-list-panes` | Show all pane IDs                |

## Notes

- CMD is sent as-is, then Enter is pressed
- For multi-line or special chars, use `tmux-type` + manual Enter
- To send without executing, use `tmux-type` instead
