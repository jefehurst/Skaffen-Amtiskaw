<p align="center">
  <img src="icon.png" alt="Skaffen-Amtiskaw" width="200">
</p>

<h1 align="center">Skaffen-Amtiskaw</h1>

<p align="center">
  <em>AI Work Assistant template for Claude Code with vendor tooling and reproducible environments.</em>
</p>

______________________________________________________________________

## What Is This?

SoS is a template repository for setting up a Claude Code work environment. It provides:

- **Reproducible development environment** via Nix flakes
- **Python/Poetry project structure** with Logseq CLI integration
- **Vendor support tools** for Ellucian and Runner Technologies products
- **Profile system** for loading domain-specific context
- **Pre-commit hooks** for code quality

## Quick Start

### Prerequisites

- [Nix](https://nixos.org/) with flakes support
- [Git](https://git-scm.com/)

Check if Nix is installed: `nix --version`

If not, install it with:

```bash
curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install
```

### Setup

1. Click the **"Use this template"** button on GitHub to create your own repository
2. Clone your new repository:

```bash
git clone git@github.com:your-username/your-repo.git
cd your-repo

# Run the initialization script
./init.sh
```

The init script will:

1. Check for Nix (and guide you through installation if needed)
2. Prompt you to name your agent
3. Update project files with your chosen name
4. Create local.env from the template
5. Run initial setup commands

### Starting Claude Code

After initialization, start your agent with:

```bash
./start.sh
```

This enters the Nix devshell and launches Claude Code with the configured environment.

**Alternative**: If you use [direnv](https://direnv.net/), run `direnv allow` to automatically load the environment when
you enter the directory. Then launch Claude Code normally.

## Configuration

### Environment Variables

Copy `local.env.example` to `local.env` and configure:

| Variable        | Description                      |
| --------------- | -------------------------------- |
| `LOGSEQ_TOKEN`  | Logseq HTTP API authentication   |
| `ELLUCIAN_USER` | Ellucian support portal username |
| `ELLUCIAN_PASS` | Ellucian support portal password |
| `RUNNER_USER`   | Runner support portal username   |
| `RUNNER_PASS`   | Runner support portal password   |

### Logseq Integration

Enable Logseq's HTTP API:

1. Open Logseq Settings
2. Go to Features
3. Enable "HTTP API"
4. Set an authentication token
5. Add that token to `local.env` as `LOGSEQ_TOKEN`

Default port: 12315

## Profiles

Profiles in `profiles/` provide domain-specific context for Claude Code. They are automatically loaded when relevant
keywords appear in conversation:

| Profile                     | Triggers                           |
| --------------------------- | ---------------------------------- |
| `logseq.md`                 | journal, logseq, lsq, block, page  |
| `ellucian.md`               | Ellucian, Banner, Colleague, Ethos |
| `runner.md`                 | Runner, CLEAN_Address              |
| `banner-troubleshooting.md` | GUBVERS, GURWADB, upgrade, ESM     |

## Vendor Support Tools

SoS includes tools for searching vendor support portals. These are used by the agent when you ask questions about vendor
products.

**Ellucian Support**: Ask the agent to search Ellucian's support portal for Banner, Colleague, Ethos, or other Ellucian
products. Example prompts:

- "Search Ellucian support for GURWADB errors"
- "Find Ellucian KB articles about Banner upgrade issues"

**Runner Technologies Support**: Ask the agent to search Runner's support portal for CLEAN_Address or other Runner
products. Example prompts:

- "Search Runner support for address validation configuration"
- "Find Runner KB articles about CLEAN_Address integration"

The agent will use the appropriate credentials from `local.env` to authenticate and search the support portals.

## Repository Structure

```
my-agent/
├── CLAUDE.md           # AI assistant instructions
├── README.md           # This file
├── TODO.md             # Current plans (maintained during work)
├── flake.nix           # Nix development environment
├── justfile            # Task runner commands
├── pyproject.toml      # Python dependencies
│
├── src/[package]/      # Main Python package (lsq CLI)
├── profiles/           # Domain-specific context profiles
├── vendor/             # Vendor support tools
│
├── docs/               # Documentation
├── ideas/              # Tabled plans and research
├── scripts/            # Utility scripts
└── tests/              # Test files
```

## Development

### Contributing Upstream

If you make improvements that could benefit other SoS users, consider contributing them back:

1. Add the upstream template as a remote:

   ```bash
   git remote add upstream git@github.com:your-org/sos.git
   ```

2. Create a branch for your changes and push to your fork

3. Open a pull request from your fork to the upstream repository

Keep upstream contributions generic—avoid including project-specific configurations or credentials.

## License

This is a template repository. Apply your own license as appropriate.
