#!/usr/bin/env bash
# Wrapper for ccstatusline that works outside the devshell
# by using direnv to activate the Nix environment.
#
# Configure in ~/.claude/settings.json:
#   {
#     "statusLine": {
#       "type": "command",
#       "command": "/path/to/your/project/scripts/ccstatusline-wrapper.sh"
#     }
#   }
#
# This wrapper is needed because Claude Code runs outside the Nix devshell,
# but ccstatusline is provided by the flake. The wrapper uses direnv to
# activate the environment before running ccstatusline.
#
# Config precedence:
#   1. ~/.config/ccstatusline/settings.json (user override)
#   2. $PROJECT_DIR/config/ccstatusline/settings.json (project default)

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Use project config if user hasn't set up their own
if [[ ! -f "$HOME/.config/ccstatusline/settings.json" ]]; then
  export XDG_CONFIG_HOME="$PROJECT_DIR/config"
fi

exec direnv exec "$PROJECT_DIR" ccstatusline "$@"
