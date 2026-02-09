{
  lib,
  stdenv,
  fetchFromGitHub,
  nodejs_22,
  makeWrapper,
}:

# Note: This package creates a wrapper that runs the MCP server via npx/tsx.
# Dependencies are cached in ~/.cache/logseq-mcp-tools on first run.
# For a fully offline/reproducible build, we'd need pnpm lockfile v9 support in nixpkgs.

stdenv.mkDerivation {
  pname = "logseq-mcp-tools";
  version = "1.0.0-unstable-2025-12-01";

  src = fetchFromGitHub {
    owner = "joelhooks";
    repo = "logseq-mcp-tools";
    rev = "cfdfc29bcac7d488690b4efd015ae79dd4280ab9";
    hash = "sha256-VvLAiyTkt2MwjMQ7GjIbupLW49GdgmO4maUCkVKth2I=";
  };

  nativeBuildInputs = [ makeWrapper ];

  dontBuild = true;

  installPhase = ''
        runHook preInstall

        # Install source files
        mkdir -p $out/lib/logseq-mcp-tools
        cp -r . $out/lib/logseq-mcp-tools/

        # Create wrapper script
        mkdir -p $out/bin
        cat > $out/bin/logseq-mcp-tools <<'WRAPPER'
    #!/usr/bin/env bash
    set -euo pipefail

    TOOL_DIR="''${XDG_CACHE_HOME:-$HOME/.cache}/logseq-mcp-tools"
    SRC_DIR="@out@/lib/logseq-mcp-tools"

    # Initialize on first run
    if [[ ! -d "$TOOL_DIR/node_modules" ]]; then
      echo "First run: installing dependencies..." >&2
      mkdir -p "$TOOL_DIR"
      cp "$SRC_DIR/package.json" "$SRC_DIR/pnpm-lock.yaml" "$SRC_DIR/index.ts" "$TOOL_DIR/"
      cp "$SRC_DIR/.env.template" "$TOOL_DIR/.env" 2>/dev/null || true
      cd "$TOOL_DIR"
      @nodejs@/bin/npm install --silent 2>/dev/null
      echo "Dependencies installed." >&2
    fi

    cd "$TOOL_DIR"
    exec @nodejs@/bin/npx tsx index.ts "$@"
    WRAPPER

        substituteInPlace $out/bin/logseq-mcp-tools \
          --replace '@out@' "$out" \
          --replace '@nodejs@' '${nodejs_22}'

        chmod +x $out/bin/logseq-mcp-tools

        runHook postInstall
  '';

  meta = with lib; {
    description = "Model Context Protocol server for Logseq knowledge graph integration";
    homepage = "https://github.com/joelhooks/logseq-mcp-tools";
    license = licenses.mit;
    maintainers = [ ];
    mainProgram = "logseq-mcp-tools";
    platforms = platforms.unix;
  };
}
