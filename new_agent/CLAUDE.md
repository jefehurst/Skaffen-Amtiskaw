# CLAUDE.md - Skaffen-Amtiskaw AI Work Assistant

## Quick Reference

| Task                  | Command                         |
| --------------------- | ------------------------------- |
| Enter dev environment | `direnv allow` or `nix develop` |
| Install Python deps   | `poetry install`                |
| Run tests             | `poetry run pytest`             |
| List tasks            | `just --list`                   |
| Task help             | `just agenthelp <recipe>`       |

## Repository Structure

```
my-agent/
├── CLAUDE.md, TODO.md, flake.nix, justfile, pyproject.toml
├── src/[package]/      # Main package (lsq CLI)
├── profiles/           # Domain-specific context (auto-loaded)
├── clients/            # Client STATUS.md files
├── ellucian-support/   # Ellucian support portal CLI
├── runner-support/     # Runner support portal CLI
└── esm-cli/            # ESM (Ellucian Solution Manager) CLI
```

## Core Principles

1. **TDD**: Write tests first. Run tests before committing. **NEVER skip tests.**
2. **Functional**: Pure functions, immutability, composition. Isolate side effects.
3. **Premortem**: Before significant features, analyze edge cases, failures, security, reuse.
4. **TODO.md**: **UPDATE EVERY TURN** during planning. Document is artifact; conversation is ephemeral.
5. **Simple over Easy**: Prefer unentangled solutions over familiar ones.
6. **Think Before Typing**: Hard problems yield to hammock time, not keyboard time.

## Environment Setup

```bash
direnv allow                    # Preferred - auto-loads devshell
nix develop                     # Manual alternative
which python3 poetry just       # Verify: should show /nix/store/... paths
```

Container workaround: See `profiles/nix-container-workaround.md` for "cannot get exit status" errors.

## Local Tools

**CRITICAL - FOLLOW THIS EXACTLY:**

1. **BEFORE** using any just recipe: Run `just --list` then `just agenthelp <recipe>`
2. **IF a tool fails**: **FIX THE TOOL.** Do NOT seek alternatives or work around it.
3. **AFTER fixing**: Update `help/<recipe>.md` with lessons learned.

## Profile System

**AUTO-LOAD when trigger keywords appear. DO NOT ask permission.**

| Profile                | Triggers                                     |
| ---------------------- | -------------------------------------------- |
| logseq.md              | journal, logseq, lsq, block                  |
| banner-troubleshooting | Banner, Oracle, GUBVERS, upgrade, ESM        |
| ellucian.md            | Ellucian, ellucian-support, Colleague, Ethos |
| runner.md              | Runner, CLEAN_Address, runner-support        |
| mcp-atlassian.md       | confluence, jira, mcp\_\_atlassian           |
| tmux.md                | tmux, pane, window, send-keys                |
| pdf-ingestion.md       | large PDF, chunk-pdf                         |

**Client mode**: When user says "[client] mode", **IMMEDIATELY** load `clients/<client>/STATUS.md`. Do NOT ask which
file.

**Updating profiles**: When user corrects a mistake, **IMMEDIATELY** add task to update the profile in that same turn.

## Code Conventions

**Python** (Sceptre standards):

- Black formatter, Flake8 linter (max line 120, complexity 12)
- Type hints everywhere, pytest for tests
- Prefer dataclasses/NamedTuple over classes with behavior
- Use `poetry add <pkg>` - **NEVER** edit pyproject.toml directly

**Shell**:

- `#!/usr/bin/env bash` + `set -euo pipefail`
- **ALWAYS** quote variables: `"$var"`

**Nix**: 2-space indent, functional style, pure expressions

**General**: 2-space indent (spaces, never tabs)

## NEVER Do These

- **NEVER** install packages globally (use flake.nix)
- **NEVER** create shell scripts when Just tasks suffice
- **NEVER** commit secrets
- **NEVER** edit pyproject.toml directly
- **NEVER** assume tool features exist - check docs first
- **NEVER** append to config files (first-match-wins semantics)
- **NEVER** assume services on localhost in containerized environments
- **NEVER** update Logseq journal unless user explicitly instructs

## Vendor Research Priority

If vendor support CLIs are installed (ellucian-support, runner-support), **ALWAYS** use them BEFORE web searches. Public
web has little useful info on enterprise products.

## ccstatusline

Config: `config/ccstatusline/settings.json` (project), `~/.config/ccstatusline/settings.json` (user override)

Widgets: model, context-length, context-percentage, tokens-total, tokens-cached, block-timer, git-branch, git-changes,
session-clock, session-cost
