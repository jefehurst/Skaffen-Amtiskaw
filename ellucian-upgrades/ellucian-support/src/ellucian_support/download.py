"""Ellucian Download Center (FlexNet Operations) client.

The Ellucian Download Center is hosted on FlexNet Operations and requires
separate SAML authentication through Okta (different from ServiceNow support).
"""

import html as html_module
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import unquote_plus, urljoin

import httpx

from .auth import AuthSession

# Okta app URL for download center
DOWNLOAD_CENTER_SSO_URL = (
    "https://sso.ellucian.com/home/ellucian_downloadcenter20_1/0oa18z5zf4pSkesMA0h8/aln18z7oubt9eltsk0h8"
)
FLEXNET_BASE = "https://ellucian.flexnetoperations.com"
DEFAULT_ORG_ID = "001G000000iHmhmIAC"  # Default organization ID


class DownloadCenterError(Exception):
    """Error from download center operations."""

    pass


@dataclass
class DownloadPackage:
    """A downloadable package (product version)."""

    name: str
    description: str
    date_available: str
    download_pkg_id: str
    org_id: str


@dataclass
class DownloadFile:
    """A downloadable file within a package."""

    name: str
    display_name: str
    size: str
    date: str
    download_url: str


class FlexNetClient:
    """Client for Ellucian Download Center (FlexNet Operations).

    Authenticates via Okta SAML and provides access to software downloads.
    """

    def __init__(
        self,
        session: AuthSession,
        progress_callback: Callable[[str], None] | None = None,
    ):
        """Initialize the FlexNet client.

        Args:
            session: Authenticated Okta session (from ellucian-support login)
            progress_callback: Optional callback for progress messages
        """
        self._okta_session = session
        self._progress = progress_callback or (lambda x: None)
        self._client: httpx.Client | None = None
        self._authenticated = False

    def _ensure_authenticated(self) -> None:
        """Authenticate to FlexNet if not already authenticated."""
        if self._authenticated and self._client:
            return

        self._progress("Authenticating to FlexNet Download Center...")

        self._client = httpx.Client(timeout=120.0, follow_redirects=False)

        # Set Okta cookies
        for name, value in self._okta_session.cookies.items():
            self._client.cookies.set(name, value)

        # Get SAML response from Okta
        resp = self._client.get(DOWNLOAD_CENTER_SSO_URL, follow_redirects=True)

        # Extract SAML form
        saml_match = re.search(r'name="SAMLResponse"[^>]*value="([^"]+)"', resp.text)
        relay_match = re.search(r'name="RelayState"[^>]*value="([^"]+)"', resp.text)
        action_match = re.search(r'<form[^>]+action="([^"]+)"', resp.text)

        if not saml_match or not action_match:
            raise DownloadCenterError("Could not get SAML response from Okta")

        saml_response = html_module.unescape(saml_match.group(1))
        relay_state = html_module.unescape(relay_match.group(1)) if relay_match else ""
        action_url = html_module.unescape(action_match.group(1))

        # Post SAML to FlexNet
        resp2 = self._client.post(
            action_url,
            data={"SAMLResponse": saml_response, "RelayState": relay_state},
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://sso.ellucian.com",
                "Referer": "https://sso.ellucian.com/",
            },
        )

        # Follow redirects
        while resp2.status_code in (301, 302, 303):
            location = resp2.headers.get("location", "")
            if not location.startswith("http"):
                location = urljoin(str(resp2.url), location)
            resp2 = self._client.get(location)

        self._authenticated = True
        self._progress("Authenticated to FlexNet")

    def list_products(self) -> list[tuple[str, str]]:
        """List all available products (download lines).

        Returns:
            List of (line_id, display_name) tuples
        """
        self._ensure_authenticated()
        assert self._client is not None

        url = f"{FLEXNET_BASE}/flexnet/operationsportal/entitledProductChart.action"
        resp = self._client.get(url)

        if resp.status_code != 200:
            raise DownloadCenterError(f"Failed to list products: {resp.status_code}")

        # Extract product links
        pattern = (
            r'href="/flexnet/operationsportal/downloadPackageVersions\.action\?'
            r'lineId=([^&"]+)&amp;orgId=([^"]+)"[^>]*>([^<]+)</a>'
        )
        matches = re.findall(pattern, resp.text)

        products = []
        seen = set()
        for line_id, org_id, name in matches:
            line_id = html_module.unescape(line_id)
            name = html_module.unescape(name).strip()
            if line_id not in seen:
                seen.add(line_id)
                products.append((line_id, name))

        return products

    def search_products(self, query: str) -> list[tuple[str, str]]:
        """Search for products matching a query.

        Args:
            query: Search string (case-insensitive)

        Returns:
            List of (line_id, display_name) tuples
        """
        all_products = self.list_products()
        query_lower = query.lower()
        return [(lid, name) for lid, name in all_products if query_lower in name.lower()]

    def get_files_for_product(self, product: str) -> list[DownloadFile]:
        """Get all downloadable files for a product (by line ID or package name).

        This is a convenience method that handles both line IDs and package names.

        Args:
            product: Either a line ID (e.g., "Ellucian-Ethos-Identity") or
                    a package name (e.g., "Ellucian - Ellucian Ethos Identity")

        Returns:
            List of downloadable files
        """
        # First try as a line ID - get packages for that product
        packages = self.get_product_packages(product)
        if packages:
            pkg = packages[0]
            # Use default org ID if not specified in package
            org_id = pkg.org_id if pkg.org_id else DEFAULT_ORG_ID
            return self.get_package_files(pkg.download_pkg_id, org_id)

        # If no packages found, treat it as a direct package ID
        return self.get_package_files(product)

    def get_package_files(
        self,
        download_pkg_id: str,
        org_id: str = "001G000000iHmhmIAC",
    ) -> list[DownloadFile]:
        """Get list of files in a download package.

        Args:
            download_pkg_id: Package ID (e.g., "Ellucian - Ellucian Ethos Identity")
            org_id: Organization ID

        Returns:
            List of downloadable files with URLs
        """
        self._ensure_authenticated()
        assert self._client is not None

        url = f"{FLEXNET_BASE}/flexnet/operationsportal/entitledDownloadFile.action"
        params = {
            "downloadPkgId": download_pkg_id,
            "orgId": org_id,
            "datatype": "file",  # Show files view
        }

        resp = self._client.get(url, params=params)
        if resp.status_code != 200:
            raise DownloadCenterError(f"Failed to get package files: {resp.status_code}")

        # Extract file download links
        # Pattern: <a href="https://download.flexnetoperations.com/...">filename</a>
        pattern = (
            r'<a\s+href="(https://download\.flexnetoperations\.com[^"]+)"[^>]*class="download-link"[^>]*>([^<]+)</a>'
        )
        matches = re.findall(pattern, resp.text, re.IGNORECASE)

        files = []
        for url, name in matches:
            url = html_module.unescape(url)
            name = html_module.unescape(name).strip()

            # Try to get size from nearby cell
            size = ""
            size_match = re.search(
                rf"{re.escape(name)}.*?<td[^>]*>([0-9.]+\s*[KMGT]?B)</td>",
                resp.text,
                re.DOTALL | re.IGNORECASE,
            )
            if size_match:
                size = size_match.group(1)

            files.append(
                DownloadFile(
                    name=name,
                    display_name=name,
                    size=size,
                    date="",
                    download_url=url,
                )
            )

        return files

    def get_product_packages(
        self,
        line_id: str,
        include_archived: bool = False,
    ) -> list[DownloadPackage]:
        """Get packages for a product line.

        Args:
            line_id: Product line ID (e.g., "Ellucian-Ethos-Identity")
            include_archived: Whether to include archived versions

        Returns:
            List of download packages
        """
        self._ensure_authenticated()
        assert self._client is not None

        packages = []

        # Get new versions
        url = f"{FLEXNET_BASE}/flexnet/operationsportal/downloadPackageVersions.action"
        params = {"lineId": line_id, "datatype": "new"}
        resp = self._client.get(url, params=params)

        if resp.status_code == 200:
            packages.extend(self._parse_packages(resp.text, line_id))

        # Get archived versions if requested
        if include_archived:
            params["datatype"] = "archive"
            resp = self._client.get(url, params=params)
            if resp.status_code == 200:
                packages.extend(self._parse_packages(resp.text, line_id))

        return packages

    def _parse_packages(self, html: str, line_id: str) -> list[DownloadPackage]:
        """Parse package list from HTML."""
        packages = []

        # Pattern for package links - orgId may be empty
        pattern = (
            r'<a\s+href="/flexnet/operationsportal/entitledDownloadFile\.action\?'
            r'downloadPkgId=([^&"]+)&(?:amp;)?orgId=([^"]*)"[^>]*>([^<]+)</a>'
        )
        matches = re.findall(pattern, html)

        for pkg_id, org_id, name in matches:
            # Decode URL-encoded characters (+ for space, %XX)
            pkg_id = unquote_plus(html_module.unescape(pkg_id))
            org_id = unquote_plus(html_module.unescape(org_id))
            name = html_module.unescape(name).strip()

            # Try to extract date
            date = ""
            date_match = re.search(
                rf"{re.escape(name)}.*?<td[^>]*>([A-Z][a-z]{{2}}\s+\d{{1,2}},\s+\d{{4}})</td>",
                html,
                re.DOTALL | re.IGNORECASE,
            )
            if date_match:
                date = date_match.group(1)

            packages.append(
                DownloadPackage(
                    name=name,
                    description=name,
                    date_available=date,
                    download_pkg_id=pkg_id,
                    org_id=org_id,
                )
            )

        return packages

    def download_file(
        self,
        file: DownloadFile,
        output_dir: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Path:
        """Download a file to the specified directory.

        Args:
            file: File to download
            output_dir: Directory to save file
            progress_callback: Optional callback(bytes_downloaded, total_bytes)

        Returns:
            Path to downloaded file
        """
        self._ensure_authenticated()
        assert self._client is not None

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / file.name

        self._progress(f"Downloading {file.name}...")

        # Stream download
        with self._client.stream("GET", file.download_url) as resp:
            if resp.status_code != 200:
                raise DownloadCenterError(f"Download failed: {resp.status_code} - {file.name}")

            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(output_path, "wb") as f:
                for chunk in resp.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback:
                        progress_callback(downloaded, total)

        self._progress(f"Downloaded {file.name}")
        return output_path

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None
        self._authenticated = False

    def __enter__(self) -> "FlexNetClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
