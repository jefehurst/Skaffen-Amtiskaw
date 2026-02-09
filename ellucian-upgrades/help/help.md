# help

Display human-readable documentation for a justfile recipe.

## Usage

```bash
just help RECIPE
```

## Examples

```bash
just help ellucian-find
just help tmux-send
just help lsq-blocks
```

## Available Documentation

Run `just --list` to see all recipes, then `just help <recipe>` for any that have documentation.

## For AI Agents

Use `just agenthelp RECIPE` for token-compressed documentation optimized for LLM context.

## Adding Documentation

Create `help/<recipe>.md` for human-readable docs and `help/<recipe>-compressed.md` for agent-optimized version.
