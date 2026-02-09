"""Configuration handling for ESM CLI."""

import os
from dataclasses import dataclass, field
from urllib.parse import urlparse


@dataclass
class ESMConfig:
    """Configuration for ESM client.

    Configuration can be loaded from:
    1. Environment variables (ESM_URL, ESM_USER, ESM_PASSWORD)
    2. Explicit parameters
    3. Config file (future)

    SSL verification is disabled by default because ESM commonly uses
    self-signed certificates.

    Tunnel mode: When ESM is only reachable through an SSH tunnel, set
    ESM_TUNNEL_URL to the local tunnel endpoint (e.g., https://localhost:8443).
    ESM_URL remains the real hostname so the Host header is set correctly.
    """

    base_url: str = ""
    tunnel_url: str = ""
    username: str = ""
    password: str = ""
    verify_ssl: bool = False
    timeout: int = 30
    esm_version: str | None = None

    # Session persistence (future)
    session_dir: str = field(default_factory=lambda: os.path.expanduser("~/.cache/esm-cli"))

    @property
    def is_tunnel(self) -> bool:
        """True if tunnel mode is configured."""
        return bool(self.tunnel_url)

    @property
    def real_host(self) -> str:
        """Hostname from ESM_URL, used for Host header in tunnel mode."""
        return urlparse(self.base_url).hostname or ""

    @property
    def real_origin(self) -> str:
        """Scheme + host (+ port if non-default) from ESM_URL."""
        parsed = urlparse(self.base_url)
        port = parsed.port
        if port and port not in (80, 443):
            return f"{parsed.scheme}://{parsed.hostname}:{port}"
        return f"{parsed.scheme}://{parsed.hostname}"

    @classmethod
    def from_env(cls) -> "ESMConfig":
        """Load configuration from environment variables.

        Environment variables:
            ESM_URL: Base URL (e.g., https://esm.example.com/admin)
            ESM_TUNNEL_URL: Local tunnel endpoint (e.g., https://localhost:8443)
            ESM_USER: Username
            ESM_PASSWORD: Password
            ESM_VERIFY_SSL: Set to "true" to enable SSL verification
            ESM_TIMEOUT: Request timeout in seconds
            ESM_VERSION: ESM version (for selector overrides)

        Returns:
            ESMConfig instance
        """
        return cls(
            base_url=os.environ.get("ESM_URL", ""),
            tunnel_url=os.environ.get("ESM_TUNNEL_URL", ""),
            username=os.environ.get("ESM_USER", ""),
            password=os.environ.get("ESM_PASSWORD", ""),
            verify_ssl=os.environ.get("ESM_VERIFY_SSL", "").lower() == "true",
            timeout=int(os.environ.get("ESM_TIMEOUT", "30")),
            esm_version=os.environ.get("ESM_VERSION"),
        )

    def validate(self) -> list[str]:
        """Validate configuration, returning list of missing fields.

        Returns:
            List of missing required field names.
        """
        missing = []
        if not self.base_url:
            missing.append("base_url (ESM_URL)")
        if not self.username:
            missing.append("username (ESM_USER)")
        if not self.password:
            missing.append("password (ESM_PASSWORD)")
        return missing
