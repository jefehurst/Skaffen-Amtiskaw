#!/usr/bin/env bash
# init.sh - Bootstrap script for Son of Stibbons (SoS)
#
# This script:
# 1. Checks for Nix (guides installation if missing)
# 2. Prompts for agent name
# 3. Renames project files and references
# 4. Creates local.env from template
# 5. Runs initial setup

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info() { echo -e "  ${BLUE}ℹ${NC}  $1"; }
success() { echo -e "  ${GREEN}✓${NC}  $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
error() { echo -e "  ${RED}✗${NC}  $1"; }
step() { echo -e "\n${CYAN}━━━${NC} ${BOLD}$1${NC} ${CYAN}━━━${NC}"; }

# Get script directory (where the repo lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo -e "${BOLD}"
echo "  ╔═══════════════════════════════════════════════════════════╗"
echo "  ║                                                           ║"
echo "  ║   🧙 Son of Stibbons (SoS) - AI Work Assistant Setup 🧙   ║"
echo "  ║                                                           ║"
echo "  ╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# -----------------------------------------------------------------------------
# Step 1: Check for Nix
# -----------------------------------------------------------------------------

step "Step 1: Checking for Nix"

check_nix() {
  if command -v nix &>/dev/null; then
    success "Nix is installed: $(nix --version)"
    return 0
  else
    return 1
  fi
}

install_nix_prompt() {
  echo ""
  error "Nix is not installed."
  echo ""
  echo "  Nix provides a reproducible development environment with all"
  echo "  the tools you need (Python, Poetry, pre-commit, etc.)."
  echo ""
  echo "  📦 To install Nix, run:"
  echo ""
  echo -e "     ${GREEN}curl --proto '=https' --tlsv1.2 -sSf -L https://install.determinate.systems/nix | sh -s -- install --no-confirm${NC}"
  echo ""
  echo "  The Determinate Systems installer:"
  echo "    • Configures flakes by default (required for this project)"
  echo "    • Works on Linux, macOS, and WSL2"
  echo "    • Can be cleanly uninstalled later"
  echo ""
  echo "  After installation, open a new terminal and run this script again."
  echo ""
  exit 1
}

if ! check_nix; then
  install_nix_prompt
fi

# Check for flakes support
if ! nix --help 2>&1 | grep -q "flake"; then
  warn "Nix flakes may not be enabled."
  echo ""
  echo "  Add to ~/.config/nix/nix.conf:"
  echo "    experimental-features = nix-command flakes"
  echo ""
fi

# -----------------------------------------------------------------------------
# Step 2: Prompt for agent name
# -----------------------------------------------------------------------------

step "Step 2: Name Your Agent"

echo ""
echo "  🤖 What would you like to name your AI assistant?"
echo ""
echo "  This name will be used for:"
echo "    • The Python package name (src/<name>/)"
echo "    • Project references in pyproject.toml"
echo "    • Documentation headers"
echo ""
echo "  Use lowercase letters, numbers, and underscores only."
echo -e "  Examples: ${CYAN}alfred${NC}, ${CYAN}jarvis${NC}, ${CYAN}friday${NC}, ${CYAN}archie${NC}"
echo ""

read -rp "  Agent name [sos]: " AGENT_NAME
AGENT_NAME="${AGENT_NAME:-sos}"

# Validate name (lowercase, numbers, underscores)
if [[ ! "$AGENT_NAME" =~ ^[a-z][a-z0-9_]*$ ]]; then
  error "Invalid name. Use lowercase letters, numbers, and underscores. Must start with a letter."
  exit 1
fi

success "Agent name: ${BOLD}$AGENT_NAME${NC}"

# -----------------------------------------------------------------------------
# Step 3: Rename project
# -----------------------------------------------------------------------------

step "Step 3: Configuring Project"

if [[ "$AGENT_NAME" != "sos" ]]; then
  info "Renaming project from 'sos' to '$AGENT_NAME'..."

  # Rename src/sos/ directory
  if [[ -d "src/sos" ]]; then
    mv "src/sos" "src/$AGENT_NAME"
    success "Renamed src/sos → src/$AGENT_NAME"
  fi

  # Update pyproject.toml
  if [[ -f "pyproject.toml" ]]; then
    sed -i "s/name = \"sos\"/name = \"$AGENT_NAME\"/g" pyproject.toml
    sed -i "s/sos\\.cli:main/$AGENT_NAME.cli:main/g" pyproject.toml
    success "Updated pyproject.toml"
  fi

  # Update src/<name>/cli.py imports
  if [[ -f "src/$AGENT_NAME/cli.py" ]]; then
    sed -i "s/from sos\\.logseq/from $AGENT_NAME.logseq/g" "src/$AGENT_NAME/cli.py"
    success "Updated cli.py imports"
  fi

  # Update CLAUDE.md placeholders
  if [[ -f "CLAUDE.md" ]]; then
    sed -i "s/\\[AGENT_NAME\\]/$AGENT_NAME/g" CLAUDE.md
    sed -i "s/\\[agent-name\\]/$AGENT_NAME/g" CLAUDE.md
    sed -i "s/\\[package\\]/$AGENT_NAME/g" CLAUDE.md
    success "Updated CLAUDE.md"
  fi

  # Update flake.nix description
  if [[ -f "flake.nix" ]]; then
    sed -i "s/Son of Stibbons/$AGENT_NAME/g" flake.nix
    success "Updated flake.nix"
  fi
else
  info "Keeping default name 'sos'"
fi

# -----------------------------------------------------------------------------
# Step 4: Create local.env
# -----------------------------------------------------------------------------

step "Step 4: Environment Configuration"

if [[ -f "local.env.example" ]] && [[ ! -f "local.env" ]]; then
  cp local.env.example local.env
  success "Created local.env from template"
  echo ""
  warn "Remember to edit local.env with your authentication tokens:"
  echo "    • LOGSEQ_TOKEN      - For Logseq HTTP API integration"
  echo "    • ELLUCIAN_USER     - For Ellucian support portal"
  echo "    • ELLUCIAN_PASS"
  echo "    • RUNNER_USER       - For Runner support portal"
  echo "    • RUNNER_PASS"
elif [[ -f "local.env" ]]; then
  info "local.env already exists, skipping"
fi

# -----------------------------------------------------------------------------
# Step 5: Atlassian MCP Setup
# -----------------------------------------------------------------------------

step "Step 5: Atlassian MCP Integration"

echo ""
echo "  Claude Code can access Jira and Confluence directly via MCP"
echo "  (Model Context Protocol). This is pre-configured in .mcp.json."
echo ""

# Check if atlassian is configured in .mcp.json
if [[ -f ".mcp.json" ]] && grep -q '"atlassian"' ".mcp.json" 2>/dev/null; then
  success "Atlassian MCP is configured"
  echo ""
  echo "  On first use, you'll be prompted to authenticate with Atlassian"
  echo "  in your browser. The hosted MCP service handles OAuth automatically."
else
  warn "Atlassian MCP is not configured in .mcp.json"
  echo ""
  read -rp "  Set up Atlassian MCP now? [Y/n] " SETUP_MCP
  SETUP_MCP="${SETUP_MCP:-y}"

  if [[ "$SETUP_MCP" =~ ^[Yy]$ ]]; then
    info "Adding Atlassian MCP..."
    nix develop --command claude mcp add atlassian https://mcp.atlassian.com/v1/sse --scope project --transport sse
    success "Atlassian MCP configured"
    echo ""
    echo "  On first use, you'll be prompted to authenticate with Atlassian"
    echo "  in your browser."
  else
    info "Skipping Atlassian MCP setup"
    echo "  Run later with:"
    echo "    claude mcp add atlassian https://mcp.atlassian.com/v1/sse --scope project --transport sse"
  fi
fi

# -----------------------------------------------------------------------------
# Step 6: Enter Nix environment and run setup
# -----------------------------------------------------------------------------

step "Step 6: Installing Dependencies"

# Try direnv first, fall back to nix develop
if command -v direnv &>/dev/null && [[ -f ".envrc" ]]; then
  direnv allow 2>/dev/null || true
fi

# Run setup in nix develop
nix develop --command bash -c '
  set -euo pipefail

  echo -e "  \033[0;34mℹ\033[0m  Installing Python dependencies..."
  poetry install --quiet

  if [[ -d ".git" ]]; then
    echo -e "  \033[0;34mℹ\033[0m  Installing pre-commit hooks..."
    pre-commit install --install-hooks >/dev/null 2>&1
    echo -e "  \033[0;32m✓\033[0m  Pre-commit hooks installed"
  else
    echo -e "  \033[1;33m⚠\033[0m  Not a git repository, skipping pre-commit hooks"
  fi

  echo -e "  \033[0;32m✓\033[0m  Dependencies installed"
'

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------

echo ""
echo -e "${GREEN}${BOLD}"
echo "  ╔═══════════════════════════════════════════════════════════╗"
echo "  ║                                                           ║"
echo "  ║              🎉 Setup Complete! 🎉                        ║"
echo "  ║                                                           ║"
echo "  ╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "  ${BOLD}Next steps:${NC}"
echo ""
echo -e "    ${CYAN}1.${NC} Edit ${CYAN}local.env${NC} with your authentication tokens"
echo ""
echo -e "    ${CYAN}2.${NC} Start working with Claude Code:"
echo -e "       ${GREEN}./start.sh${NC}"
echo ""
echo -e "    ${CYAN}3.${NC} Or enter the dev environment manually:"
echo -e "       ${GREEN}direnv allow${NC}  or  ${GREEN}nix develop${NC}"
echo ""
echo -e "    ${CYAN}4.${NC} See available commands:"
echo -e "       ${GREEN}just --list${NC}"
echo ""
echo -e "  ${CYAN}Happy hacking! 🚀${NC}"
echo ""
