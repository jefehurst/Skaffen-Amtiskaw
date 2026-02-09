# ESM CLI

Command-line tool for Ellucian Solution Manager automation.

## Status

**Planning phase** - collecting fixtures from ESM instance.

## Documentation

- [PLAN.md](PLAN.md) - Architecture, technical decisions, project structure
- [STORIES.md](STORIES.md) - User stories, HAR capture guides

## Directory Structure

```
esm-cli/
├── README.md
├── PLAN.md           # Architecture and technical decisions
├── STORIES.md        # User stories and capture guides
└── fixtures/
    ├── har/          # HAR captures from browser DevTools
    └── html/         # Extracted HTML for unit tests
```

## Fixture Capture

See [STORIES.md](STORIES.md) for:

- Manual HAR capture instructions
- Agent HTTP exploration protocol
- File naming conventions
