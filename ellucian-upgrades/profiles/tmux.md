# Profile: tmux

Load this profile when working inside a tmux session or when the user needs to coordinate across terminal panes/windows.

## Information Lookup Priority

1. **tmux man page** - `man tmux` is comprehensive; search there first
2. **tmux list-commands** - Shows all available commands with synopsis
3. **tmux list-keys** - Shows current key bindings
4. **Web search** - For complex workflows or troubleshooting

## Claude Code + tmux Integration

Claude Code runs in a terminal, which may be inside a tmux pane. This enables powerful workflows:

### Discovering Current Context

```bash
# Where am I?
tmux display-message -p "Session: #S, Window: #W, Pane: #P"

# List all panes across all sessions
tmux list-panes -a -F "#{session_name}:#{window_index}.#{pane_index} #{pane_id} #{pane_current_command}"

# Current pane ID (for use in -t flags)
tmux display-message -p "#{pane_id}"
```

### Target Syntax

tmux uses a consistent target syntax:

| Format                  | Example    | Description                       |
| ----------------------- | ---------- | --------------------------------- |
| `session:window.pane`   | `main:0.1` | Fully qualified                   |
| `:window.pane`          | `:1.0`     | Current session, window 1, pane 0 |
| `.pane`                 | `.1`       | Current window, pane 1            |
| `{last}`                | `{last}`   | Previously active pane            |
| `{next}` / `{previous}` | `{next}`   | Next/previous pane in window      |
| `%N` (pane ID)          | `%38`      | Direct pane ID (most reliable)    |

### Sending Commands to Other Panes

```bash
# Send a command to another pane (pane 1 in current window)
tmux send-keys -t .1 'ls -la' Enter

# Send to a specific window (window "bash" in current session)
tmux send-keys -t :bash 'echo hello' Enter

# Send literal keys (useful for special chars)
tmux send-keys -t .1 -l 'some text'

# Send without Enter (just type, don't execute)
tmux send-keys -t .1 'partial command'

# Clear target pane first, then send
tmux send-keys -t .1 C-c C-l 'fresh command' Enter
```

### Capturing Pane Output

```bash
# Capture visible content of another pane
tmux capture-pane -t .1 -p

# Capture including scrollback (last 100 lines)
tmux capture-pane -t .1 -p -S -100

# Capture full history
tmux capture-pane -t .1 -p -S -

# Capture to a file
tmux capture-pane -t .1 -p > /tmp/pane-output.txt
```

### Waiting for Command Completion

```bash
# In the target pane, signal when done
tmux send-keys -t .1 'long-command; tmux wait-for -S done' Enter

# In Claude's pane, wait for that signal
tmux wait-for done
echo "Command finished!"
```

**Caution**: `wait-for` blocks indefinitely if the signal never arrives. Always have a timeout plan.

### Creating and Managing Panes

```bash
# Split current window horizontally (top/bottom)
tmux split-window -v

# Split vertically (left/right)
tmux split-window -h

# Split and run a command
tmux split-window -v 'htop'

# Create new window
tmux new-window -n 'monitoring'

# Kill a pane
tmux kill-pane -t .1
```

## Common Patterns for AI Assistants

### Pattern: Run Command in Background Pane

When Claude needs to run a long process while continuing to work:

```bash
# Create a new pane, run the command there
tmux split-window -v -d 'npm run build 2>&1 | tee /tmp/build.log'

# Check output later
cat /tmp/build.log

# Or capture live
tmux capture-pane -t {last} -p | tail -20
```

### Pattern: Monitor a Service

```bash
# Start service in another pane
tmux send-keys -t :1.0 'docker logs -f mycontainer' Enter

# Later, capture recent output
tmux capture-pane -t :1.0 -p -S -50 | grep -i error
```

### Pattern: Interactive Debugging

```bash
# Send to a REPL or debugger pane
tmux send-keys -t .1 'print(variable_name)' Enter

# Wait briefly, then capture output
sleep 0.5
tmux capture-pane -t .1 -p | tail -5
```

### Pattern: Coordinate Multiple Services

```bash
# Start services in different windows
tmux send-keys -t :api 'npm run api' Enter
tmux send-keys -t :frontend 'npm run dev' Enter
tmux send-keys -t :db 'docker-compose up postgres' Enter

# Check all are running
for w in api frontend db; do
  echo "=== $w ==="
  tmux capture-pane -t :$w -p | tail -3
done
```

## Key References

| Command           | Purpose                            |
| ----------------- | ---------------------------------- |
| `send-keys`       | Type into another pane             |
| `capture-pane`    | Read content from another pane     |
| `wait-for`        | Synchronize between panes          |
| `display-message` | Get info about current context     |
| `list-panes`      | Discover available panes           |
| `split-window`    | Create new panes                   |
| `select-pane`     | Switch active pane                 |
| `run-shell`       | Execute command and capture output |

## Common Options

### send-keys Flags

| Flag | Purpose                                |
| ---- | -------------------------------------- |
| `-t` | Target pane                            |
| `-l` | Literal mode (disable key name lookup) |
| `-R` | Reset terminal state first             |
| `-H` | Expect hex key codes                   |

### capture-pane Flags

| Flag | Purpose                                       |
| ---- | --------------------------------------------- |
| `-t` | Target pane                                   |
| `-p` | Print to stdout (instead of paste buffer)     |
| `-S` | Start line (negative = scrollback, `-` = all) |
| `-E` | End line                                      |
| `-e` | Include escape sequences (colors)             |
| `-J` | Join wrapped lines                            |

## Gotchas and Edge Cases

### Timing Issues

Commands sent via `send-keys` execute asynchronously. If you need output, either:

1. Use `wait-for` for explicit synchronization
2. Add a `sleep` delay (fragile but simple)
3. Poll with `capture-pane` until expected output appears

### Special Characters

Some characters need escaping or literal mode:

```bash
# Backslash
tmux send-keys -t .1 'echo "path\\to\\file"' Enter

# Semicolon (tmux command separator)
tmux send-keys -t .1 'cmd1; cmd2' Enter  # Works in modern tmux

# For complex strings, use -l (literal)
tmux send-keys -t .1 -l 'complex $string with "quotes"'
tmux send-keys -t .1 Enter
```

### Pane IDs vs Indexes

Pane indexes (0, 1, 2...) can change when panes are created/destroyed. Pane IDs (`%38`, `%39`...) are stable. For
reliable targeting in scripts, prefer pane IDs:

```bash
# Get pane ID
PANE_ID=$(tmux display-message -t .1 -p "#{pane_id}")
# Use it reliably
tmux send-keys -t "$PANE_ID" 'command' Enter
```

### Detached Sessions

Claude can interact with panes in detached sessions:

```bash
# List all sessions
tmux list-sessions

# Send to detached session's pane
tmux send-keys -t mysession:0.0 'background task' Enter
```

## Environment Variables

| Variable    | Purpose                                      |
| ----------- | -------------------------------------------- |
| `TMUX`      | Set when inside tmux (socket path)           |
| `TMUX_PANE` | Current pane ID (e.g., `%38`)                |
| `TERM`      | Usually `screen-256color` or `tmux-256color` |

Check if in tmux:

```bash
if [ -n "$TMUX" ]; then
  echo "Inside tmux"
fi
```

## Just Recipes

This project includes just recipes for common tmux operations. Use `just --list | grep tmux` to see all.

| Recipe                                | Purpose                                       |
| ------------------------------------- | --------------------------------------------- |
| `just tmux-check`                     | Check if in tmux, show context                |
| `just tmux-context`                   | Show detailed session/window/pane info        |
| `just tmux-list-panes`                | List all panes across all sessions            |
| `just tmux-list-windows`              | List windows in current session               |
| `just tmux-title X`                   | Set current window title                      |
| `just tmux-alert "X"`                 | Display message + flash bell                  |
| `just tmux-send :1.0 "cmd"`           | Send command to pane and execute              |
| `just tmux-type :1.0 "text"`          | Type text without Enter                       |
| `just tmux-capture :1.0`              | Capture visible pane content                  |
| `just tmux-capture-full :1.0 500`     | Capture with scrollback                       |
| `just tmux-tail :1.0 20`              | Get last N lines from pane                    |
| `just tmux-grep :1.0 "error"`         | Search pane output                            |
| `just tmux-spawn-window "name" "cmd"` | New window with command                       |
| `just tmux-spawn-bg "cmd"`            | Background pane (split, no focus)             |
| `just tmux-run-wait "cmd"`            | Run in new window, wait for completion        |
| `just tmux-pane-status :1.0`          | Check if pane is idle or running              |
| `just tmux-wait-idle :1.0`            | Block until pane returns to shell             |
| `just tmux-exec :1.0 "cmd"`           | Run command, capture output synchronously     |
| `just tmux-interrupt :1.0`            | Send Ctrl+C to pane                           |
| `just tmux-monitor :1.0`              | Check worker state (complete/waiting/working) |
| `just tmux-await :1.0 "SIG" 30 300`   | Wait for completion signal with polling       |
| `just tmux-clear :1.0`                | Clear pane (Ctrl+C, Ctrl+L)                   |
| `just tmux-flash :1.0`                | Flash pane background yellow                  |
| `just tmux-kill-pane :1.0`            | Kill target pane                              |
| `just tmux-kill-window :1`            | Kill target window                            |
| `just tmux-claude`                    | Spawn new Claude Code session in new window   |
| `just tmux-claude "name"`             | Spawn with custom window name                 |
| `just tmux-sessions`                  | List all Claude sessions for this project     |

### Team Leader Mode

Use the `/lead` slash command to enter Team Leader mode, which provides:

- Patterns for spawning and coordinating multiple Claude workers
- Task assignment and monitoring protocols
- Best practices for parallel work coordination

### Target Syntax Quick Reference

- `:1.0` = Window 1, pane 0 (in current session)
- `.1` = Pane 1 in current window
- `:bash.0` = Window named "bash", pane 0
- `%38` = Pane ID (stable, from `just tmux-list-panes`)

## Behavioral Corrections

This section collects corrections and refinements from actual sessions. Update immediately when the user provides
corrections or useful insights.

### 2024-12-14 - Always verify prompt submission to Claude Code workers

**Problem**: Sent prompts to worker panes via `tmux send-keys` without verifying they submitted. Prompts got stuck when
workers were at permission prompts, wasting time polling for completion that would never happen.

**Correction**: After sending any prompt to a worker:

1. Wait briefly (`sleep 2`)
2. Capture pane output and check:
   - `(esc to interrupt)` visible = prompt submitted, worker processing
   - Text still in `> ` prompt line = NOT submitted
   - Permission prompt visible = worker was blocked, text went wrong place

**Pattern**:

```bash
tmux send-keys -t :worker "task" Enter
sleep 2 && tmux capture-pane -t :worker -p | tail -10
# Verify (esc to interrupt) appears or > line is empty
```

**Context**: Claude Code shows various activity words ("Thinking", "Working", etc.) but the reliable indicator of
processing is `(esc to interrupt)`. Permission prompts ("Do you want to proceed?") intercept input.

______________________________________________________________________

## Consolidation Log

Review after ~10 corrections. Promote patterns to main sections, archive one-offs.

*No consolidations yet.*
