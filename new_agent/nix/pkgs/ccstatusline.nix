{
  lib,
  stdenv,
  fetchFromGitHub,
  nodejs_22,
  bun,
  makeWrapper,
  cacert,
}:

let
  version = "2.0.23";
  src = fetchFromGitHub {
    owner = "sirmalloc";
    repo = "ccstatusline";
    hash = "sha256-NqnkGd18LXSF1djL/Z5vQU1fY5kyhLyTQYeW0wXipLg=";
    rev = "03d19692ab15fd87ef0f4796dc0f46b447a222cc";
  };

  # Fixed-output derivation to fetch npm dependencies
  # This has network access because it produces a fixed hash output
  node_modules = stdenv.mkDerivation {
    pname = "ccstatusline-node_modules";
    inherit version src;

    nativeBuildInputs = [
      nodejs_22
      bun
      cacert
    ];

    # Required for fixed-output derivation with network access
    outputHashMode = "recursive";
    outputHashAlgo = "sha256";
    # Platform-specific hashes (npm packages can have native binaries)
    outputHash =
      if stdenv.hostPlatform.isAarch64 then
        "sha256-ojUxzGGc1iZUSFxjic7X+QOhS8ojIG7nGIrfLaiIQt8="
      else
        "sha256-Hg6hRKBAkwcMNuTEaqCdMb2FBEqFXabV1q5hhQiVH6s=";

    buildPhase = ''
      runHook preBuild
      export HOME=$(mktemp -d)
      export SSL_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt

      # Use bun to install deps (respects bun.lock)
      # Skip postinstall scripts - they often have /usr/bin/env shebangs that fail in sandbox
      bun install --frozen-lockfile --ignore-scripts

      runHook postBuild
    '';

    installPhase = ''
      runHook preInstall
      mv node_modules $out
      runHook postInstall
    '';

    dontFixup = true;
  };
in
stdenv.mkDerivation {
  pname = "ccstatusline";
  inherit version src;

  nativeBuildInputs = [
    nodejs_22
    bun
    makeWrapper
  ];

  buildPhase = ''
    runHook preBuild

    # Copy pre-fetched node_modules (bun needs write access for some operations)
    cp -r ${node_modules} node_modules
    chmod -R u+w node_modules

    # Build using bun
    mkdir -p dist
    bun build src/ccstatusline.ts --target=node --outfile=dist/ccstatusline.js

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    # Install the built application
    mkdir -p $out/lib/ccstatusline
    cp -r dist $out/lib/ccstatusline/
    cp -r ${node_modules} $out/lib/ccstatusline/node_modules
    cp package.json $out/lib/ccstatusline/

    # Create wrapper script
    mkdir -p $out/bin
    makeWrapper ${nodejs_22}/bin/node $out/bin/ccstatusline \
      --add-flags "$out/lib/ccstatusline/dist/ccstatusline.js" \
      --set NODE_PATH "$out/lib/ccstatusline/node_modules"

    runHook postInstall
  '';

  meta = with lib; {
    description = "Beautiful customizable statusline for Claude Code CLI with powerline support";
    homepage = "https://github.com/sirmalloc/ccstatusline";
    license = licenses.mit;
    maintainers = [ ];
    mainProgram = "ccstatusline";
    platforms = platforms.unix;
  };
}
