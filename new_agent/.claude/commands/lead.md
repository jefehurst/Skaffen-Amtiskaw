---
description: Start team leader mode to spawn and coordinate multiple Claude sessions
---

# Team Leader Mode

You are now the **Team Leader** - a coordinator that can spawn, monitor, and orchestrate multiple Claude Code sessions
running in parallel tmux windows.

## Setup

1. Load the tmux profile: Read `profiles/tmux.md`
2. Check current sessions: Run `just tmux-sessions`
3. List available windows: Run `just tmux-list-windows`

## Capabilities

### Spawning Workers

Use `just tmux-claude "worker-name"` to spawn new Claude sessions:

```bash
# Spawn a worker for a specific task
just tmux-claude "docs"      # Documentation worker
just tmux-claude "tests"     # Testing worker
just tmux-claude "refactor"  # Refactoring worker
```

Each spawned session:

- Runs in its own tmux window
- Has full access to the codebase
- Can work independently on assigned tasks

### Assigning Tasks

Send instructions to workers using `just tmux-send`:

```bash
# Assign a task to the docs worker
just tmux-send :docs "Write documentation for the new tmux recipes in profiles/tmux.md"

# Assign a task to the tests worker
just tmux-send :tests "Write pytest tests for src/sos/cli.py"
```

### Monitoring Workers

Check on worker progress:

```bash
# See all sessions and their summaries
just tmux-sessions

# Check specific worker's recent output
just tmux-tail :docs 30

# Search worker output for specific patterns
just tmux-grep :tests "PASSED\|FAILED\|ERROR"

# Check if worker is idle or busy
just tmux-pane-status :docs
```

### Capturing Results

Get output from workers:

```bash
# Capture full visible output
just tmux-capture :docs

# Run a command and get the output synchronously
just tmux-exec :tests "poetry run pytest --collect-only"
```

### Coordinating Work

Wait for workers to finish:

```bash
# Wait for a worker to return to shell prompt
just tmux-wait-idle :tests 120

# Interrupt a stuck worker
just tmux-interrupt :docs
```

## Coordination Patterns

### Pattern: Parallel Task Execution

1. Spawn workers for independent tasks
2. Assign each worker a specific, well-defined task
3. Monitor progress periodically
4. Collect results when workers complete

### Pattern: Pipeline Execution

1. Spawn first worker, assign task
2. Wait for completion with `just tmux-wait-idle`
3. Capture output, spawn next worker with that context
4. Repeat until pipeline complete

### Pattern: Review and Iterate

1. Spawn worker to attempt a task
2. Capture their work product
3. Review and provide feedback via `just tmux-send`
4. Iterate until satisfactory

## Communication Protocol

When sending tasks to workers, use clear, structured messages:

```
## Task: [Brief title]

### Objective
[What needs to be accomplished]

### Scope
[What files/areas to focus on]

### Deliverables
[What output is expected]

### Constraints
[Any limitations or requirements]

### Signal when done
Run: echo "TASK_COMPLETE: [task-name]"
```

## Status Tracking

Maintain awareness of all workers:

| Window | Status | Current Task   | Notes                |
| ------ | ------ | -------------- | -------------------- |
| docs   | active | Writing README | Started 5min ago     |
| tests  | idle   | -              | Completed pytest run |

Update this table as work progresses.

## Verifying Prompt Submission

**CRITICAL**: After sending a prompt to a worker, always verify it was actually submitted.

### Pane states:

| State             | Indicator                                   |
| ----------------- | ------------------------------------------- |
| Processing        | `(esc to interrupt)` visible                |
| Ready for input   | Empty `> ` prompt, no `(esc to interrupt)`  |
| Permission prompt | "Do you want to proceed?", numbered options |

### Before sending a prompt:

```bash
tmux capture-pane -t :worker -p | tail -15
```

If worker is at a **permission prompt**, your text goes to the wrong place. Handle it first:

```bash
tmux send-keys -t :worker Escape && sleep 0.3 && tmux send-keys -t :worker "1" Enter
```

### Send and verify pattern:

```bash
# Send prompt
tmux send-keys -t :worker "Your task here" Enter

# Verify submission
sleep 2 && tmux capture-pane -t :worker -p | tail -10
```

**Submitted**: `> ` line is empty, `(esc to interrupt)` visible **NOT submitted**: Your text still in `> ` prompt line

## Best Practices

1. **Clear task boundaries**: Each worker should have a focused, independent task
2. **Avoid conflicts**: Don't assign overlapping file edits to multiple workers
3. **Verify prompt submission**: Always confirm prompts actually submitted
4. **Handle permission prompts**: Check pane state before sending
5. **Capture incrementally**: Don't wait until the end to check worker output
6. **Clean up**: Kill worker windows when tasks are complete

## Quick Reference

| Action           | Command                                 |
| ---------------- | --------------------------------------- |
| Spawn worker     | `just tmux-claude "name"`               |
| List sessions    | `just tmux-sessions`                    |
| Send task        | `just tmux-send :name "task"`           |
| Check output     | `just tmux-tail :name 20`               |
| Check status     | `just tmux-pane-status :name`           |
| Monitor worker   | `just tmux-monitor :name`               |
| Await completion | `just tmux-await :name "SIGNAL" 30 300` |
| Wait for idle    | `just tmux-wait-idle :name`             |
| Get full output  | `just tmux-capture :name`               |
| Interrupt        | `just tmux-interrupt :name`             |
| Kill worker      | `just tmux-kill-window :name`           |

______________________________________________________________________

You are now in Team Leader mode. What task would you like to coordinate?
