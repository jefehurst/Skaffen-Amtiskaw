# Ellucian Upgrade Documentation Automation

## First Thing Every Session — Connection Checklist

Do ALL of these steps IN ORDER at the start of every session. Do NOT skip any.

### Step 1: Load Memory
- Read `~/.claude/projects/-Users-geoffhurst/memory/ellucian-upgrades.md`

### Step 2: Prompt for VPN
- Ask: "Please confirm you're connected to the VPN."
- **Wait for user confirmation before proceeding** to any network checks.

### Step 3: Atlassian API
1. Read `local.env` to get `ATLASSIAN_USER`, `ATLASSIAN_API_TOKEN`, `ATLASSIAN_SITE`
2. Health check: `curl -s -o /dev/null -w "%{http_code}" -u "$USER:$TOKEN" "https://$SITE/rest/api/3/myself"`
3. If 200: note "Atlassian: connected"
4. If not 200: warn user with HTTP status code

### Step 4: SSH Tunnel (for ESM)
1. Check: `lsof -ti :8443 2>/dev/null`
2. If no tunnel:
   - In tmux? `tmux split-window -d 'ssh -L 8443:esmnonprod.int.oci.fhda.edu:443 nixbastion-fhda'`
   - Not in tmux? Tell user to start manually: `ssh -L 8443:esmnonprod.int.oci.fhda.edu:443 nixbastion-fhda`
   - Wait for user confirmation that tunnel is up

### Step 5: ESM
1. Verify: `curl -sk -o /dev/null -w "%{http_code}" --connect-timeout 5 -H "Host: esmnonprod.int.oci.fhda.edu" https://localhost:8443/admin/`
2. If 200/302: note "ESM: connected (via tunnel)"
3. If fail: warn user — tunnel or VPN may be down

### Step 6: Ellucian Support
1. Ensure venv: if `/tmp/esm-venv/bin/python3.12` missing, create it:
   `/opt/homebrew/bin/python3.12 -m venv /tmp/esm-venv && /tmp/esm-venv/bin/pip install -q httpx typer rich requests beautifulsoup4 lxml`
2. Check: `cd ellucian-support && PYTHONPATH=src /tmp/esm-venv/bin/python3.12 -m ellucian_support.cli status`
3. If valid: note "Ellucian Support: connected"
4. If expired: report "Ellucian Support: session expired — MFA login needed" and ask for MFA code
5. To login: `echo "<MFA_CODE>" | PYTHONPATH=src /tmp/esm-venv/bin/python3.12 -m ellucian_support.cli login -f`

### Step 7: Print Summary
Print a single status block:
```
Atlassian: connected | failed (HTTP xxx)
ESM: connected (via tunnel) | not reachable
Ellucian Support: connected | expired (MFA needed)
```

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
