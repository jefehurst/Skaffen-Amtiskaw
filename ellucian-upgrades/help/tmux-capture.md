# tmux-capture

Capture visible content from another tmux pane.

## Usage

```bash
# Visible area only
just tmux-capture TARGET

# With scrollback history
just tmux-capture-full TARGET [LINES]
```

## Arguments

| Arg    | Description                         |
| ------ | ----------------------------------- |
| TARGET | Pane identifier (e.g., `%42`)       |
| LINES  | Lines of scrollback (default: 1000) |

## Examples

```bash
# Capture visible content
just tmux-capture %42

# Capture with 500 lines of history
just tmux-capture-full %42 500

# Capture and grep for pattern
just tmux-capture %42 | grep "error"
```

## Output

Raw pane content, including:

- Command prompts
- Command output
- Any visible text

## Related Recipes

| Recipe            | Purpose                        |
| ----------------- | ------------------------------ |
| `tmux-tail`       | Last N lines only              |
| `tmux-grep`       | Search pane output             |
| `tmux-exec`       | Run command and capture result |
| `tmux-list-panes` | Find pane IDs                  |

## Notes

- Visible area is what fits in pane dimensions
- Use `tmux-capture-full` for scrollback
- Output includes ANSI codes; pipe through `cat -v` if needed
