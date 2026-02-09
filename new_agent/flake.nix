{
  description = "Skaffen-Amtiskaw - Ellucian Banner Upgrade Documentation Assistant";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { nixpkgs, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        # Custom packages
        logseq-mcp-tools = pkgs.callPackage ./nix/pkgs/logseq-mcp-tools.nix { };
        ccstatusline = pkgs.callPackage ./nix/pkgs/ccstatusline.nix { };
      in
      {
        packages = {
          inherit logseq-mcp-tools ccstatusline;
          default = logseq-mcp-tools;
        };

        devShells.default = pkgs.mkShell {
          packages = [
            # Core tools
            pkgs.pre-commit
            pkgs.just
            pkgs.watchexec
            pkgs.delta

            # Python
            pkgs.python312
            pkgs.poetry

            # Node.js (for MCP tools)
            pkgs.nodejs_22

            # MCP servers
            logseq-mcp-tools

            # AI assistant
            pkgs.claude-code
            ccstatusline

            # Terminal sharing
            pkgs.tmate
            pkgs.upterm

            # WebSocket tunnel (SSH through corporate proxies)
            pkgs.wstunnel

            # GitHub CLI
            pkgs.gh

            # AWS CLI
            pkgs.awscli2
            pkgs.jq

            # TUI tools
            pkgs.gum

            # Nix linting and formatting
            pkgs.statix
            pkgs.deadnix
            pkgs.nixfmt-rfc-style

            # Shell linting and formatting
            pkgs.shellcheck
            pkgs.shfmt

            # Java decompilation (for WAR/JAR analysis)
            pkgs.jdk21
            pkgs.cfr
            pkgs.unzip

            # Make sure nix works within the shell
            pkgs.nixStatic
          ];

          shellHook = ''
            # Load local environment variables if present
            if [[ -f "$PWD/local.env" ]]; then
              set -a
              source "$PWD/local.env"
              set +a

              # Also export lowercase proxy vars (some tools only check lowercase)
              [[ -n "''${HTTP_PROXY:-}" ]] && export http_proxy="$HTTP_PROXY"
              [[ -n "''${HTTPS_PROXY:-}" ]] && export https_proxy="$HTTPS_PROXY"
              [[ -n "''${NO_PROXY:-}" ]] && export no_proxy="$NO_PROXY"
            fi

            # Uncomment to auto-install Python deps on shell entry:
            # poetry install --quiet
          '';
        };
      }
    );
}
