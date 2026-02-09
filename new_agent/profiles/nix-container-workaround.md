# Nix Container Workaround Profile

This profile covers workarounds for running Nix in containerized environments where the Nix daemon doesn't work
properly.

## The Problem

**Known Issue**: In containerized environments (like Claude Code web sessions), the Nix daemon fails with:

```
cannot get exit status of PID XXXX: No child processes
```

**Root cause**: Container PID namespace isolation prevents Nix from using `waitpid()` to get child process exit status.
This affects all Nix commands (`nix develop`, `nix print-dev-env`) and therefore direnv (which calls `use flake`
internally). The packages still download to `/nix/store` before the crash.

**Why direnv/nix develop don't work here**: Both methods require the Nix daemon to spawn and manage child processes. The
container would need `--pid=host` or equivalent for Nix to work properly.

## Workaround Sequence

1. Run the Determinate installer (will fail at the end but populates /nix/store):

   ```bash
   curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install --no-confirm
   ```

2. Find the nix binary and trigger package downloads:

   ```bash
   NIX_BIN=$(find /nix/store -maxdepth 1 -name "*-determinate-nix-*" -type d | head -1)/bin
   export PATH="$NIX_BIN:$PATH"
   nix develop --command true 2>/dev/null || true
   ```

   (This also may fail, but downloads flake packages to /nix/store)

3. Source the workaround script to set up PATH:

   ```bash
   source scripts/nix-env.sh
   ```

4. Verify tools are available:

   ```bash
   which python3 poetry
   # Should all show /nix/store/... paths
   ```

## After the Workaround

Once `nix-env.sh` is sourced, you can use `poetry run` for Python commands:

```bash
poetry install                    # Install Python deps
poetry run python -m package.cli  # Run CLI tools
poetry run pytest                 # Run tests
```

## Alternative: Using `just do` Wrapper

When not in an active devshell, the justfile provides a wrapper:

```bash
just do "poetry install"
just do "poetry run pytest"
```

This runs commands inside `nix develop`, but requires Nix to be properly functional (won't work in broken container
environments).

## Verifying Your Environment

Before running project commands, verify the devshell is active:

```bash
which python3 poetry just  # Should show /nix/store/... paths
poetry --version           # Should work
```

If tools aren't found, follow the workaround steps above.
