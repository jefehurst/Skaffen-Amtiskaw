# tmux-exec

Execute command in another pane and capture the output synchronously.

## Usage

```bash
just tmux-exec TARGET CMD
```

## Arguments

| Arg    | Description                   |
| ------ | ----------------------------- |
| TARGET | Pane identifier (e.g., `%42`) |
| CMD    | Command to execute            |

## How It Works

1. Sends Ctrl+C to cancel any partial input
2. Sends command with unique marker
3. Polls until marker appears in output
4. Extracts and returns command output
5. Times out after 60 seconds

## Examples

```bash
# Run command and get output
just tmux-exec %42 "pwd"

# Check git status in another pane
just tmux-exec %42 "git status"

# Run build and capture result
just tmux-exec %42 "npm run build"
```

## Output

Command stdout only (marker and prompt filtered out).

## Limitations

- 60 second timeout
- Assumes pane has a shell prompt
- May not work with interactive commands
- Sends Ctrl+C first (interrupts running commands)

## Related Recipes

| Recipe             | Purpose                           |
| ------------------ | --------------------------------- |
| `tmux-send`        | Fire-and-forget command           |
| `tmux-capture`     | Read without executing            |
| `tmux-wait-idle`   | Wait for pane to return to prompt |
| `tmux-pane-status` | Check if pane is idle or running  |

## When to Use

- Need command output for decision making
- Want to verify a command completed
- Building automation that depends on results

## Troubleshooting

**Timeout**: Command took >60s or pane isn't at shell prompt.

**Empty output**: Command may have failed or produced no stdout.

**Interrupted something**: Ctrl+C is sent first; ensure pane is idle.
