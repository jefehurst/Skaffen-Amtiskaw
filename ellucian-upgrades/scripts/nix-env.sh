#!/usr/bin/env bash
# nix-env.sh - Container environment workaround
#
# This script sets up PATH to use tools from /nix/store when the
# Nix daemon isn't fully functional (e.g., in containerized environments).
#
# Usage: source scripts/nix-env.sh
#
# Customize the PACKAGES array below with your project's dependencies.

set -euo pipefail

# =============================================================================
# CONFIGURATION
# =============================================================================
# Add patterns for packages your project needs.
# These are glob patterns that match package names in /nix/store.
# Format: "pattern" or "pattern|grep_exclude"
#
# Examples:
#   "python3-3.1*"                    - Python 3.1x
#   "python3.12-poetry-*|core"        - Poetry, excluding poetry-core
#   "nodejs-*"                        - Node.js
#   "ffmpeg-*-bin"                    - FFmpeg binary
#
declare -A PACKAGES=(
  ["python"]="python3-3.1*"
  ["poetry"]="python3.13-poetry-*|core"
  ["just"]="just-*"
  # Add your project-specific packages below:
  # ["nodejs"]="nodejs-*"
  # ["ffmpeg"]="ffmpeg-*-bin"
)

# Optional: Environment variables to set based on found packages
# Format: PACKAGE_NAME:VAR_NAME:SUBPATH
# Example: espeak:ESPEAK_DATA_PATH:/share/espeak-ng-data
ENV_VARS=(
  # "espeak:ESPEAK_DATA_PATH:/share/espeak-ng-data"
)

# =============================================================================
# IMPLEMENTATION (no need to modify below this line)
# =============================================================================

# Find packages in /nix/store
find_nix_pkg() {
  local pattern="$1"
  local exclude="${2:-}"

  if [[ -n "$exclude" ]]; then
    find /nix/store -maxdepth 1 -type d -name "*-${pattern}" 2>/dev/null \
      | grep -v "$exclude" \
      | grep -v drv \
      | head -1
  else
    find /nix/store -maxdepth 1 -type d -name "*-${pattern}" 2>/dev/null \
      | grep -v drv \
      | head -1
  fi
}

# Also look for determinate nix binary
NIX_BIN=$(find_nix_pkg "determinate-nix-*" "")

# Build PATH from found packages
NIX_PATH_ADDITIONS=""

# Add Nix binary if found
if [[ -n "$NIX_BIN" && -d "$NIX_BIN/bin" ]]; then
  NIX_PATH_ADDITIONS="${NIX_BIN}/bin"
fi

# Process each package
declare -A FOUND_PACKAGES
for name in "${!PACKAGES[@]}"; do
  spec="${PACKAGES[$name]}"

  # Split on | for pattern and exclude
  if [[ "$spec" == *"|"* ]]; then
    pattern="${spec%%|*}"
    exclude="${spec#*|}"
  else
    pattern="$spec"
    exclude=""
  fi

  pkg=$(find_nix_pkg "$pattern" "$exclude")
  FOUND_PACKAGES[$name]="$pkg"

  if [[ -n "$pkg" && -d "$pkg/bin" ]]; then
    NIX_PATH_ADDITIONS="${NIX_PATH_ADDITIONS}:${pkg}/bin"
  fi
done

# Remove leading colon and export
NIX_PATH_ADDITIONS="${NIX_PATH_ADDITIONS#:}"
export PATH="${NIX_PATH_ADDITIONS}:${PATH}"

# Set up environment variables
for env_spec in "${ENV_VARS[@]}"; do
  pkg_name="${env_spec%%:*}"
  remainder="${env_spec#*:}"
  var_name="${remainder%%:*}"
  subpath="${remainder#*:}"

  pkg_path="${FOUND_PACKAGES[$pkg_name]:-}"
  if [[ -n "$pkg_path" ]]; then
    export "$var_name"="${pkg_path}${subpath}"
  fi
done

# Print status
echo "=== Nix Environment Setup ==="
for name in "${!PACKAGES[@]}"; do
  # Find the likely binary name (usually same as package name)
  binary="$name"
  case "$name" in
    python) binary="python3" ;;
      # Add custom mappings as needed
  esac

  location=$(which "$binary" 2>/dev/null || echo "NOT FOUND")
  printf "%-12s %s\n" "${name}:" "$location"
done
echo "==========================="
