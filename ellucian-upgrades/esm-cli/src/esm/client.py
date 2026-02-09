"""ESM HTTP client with session management and response validation."""

import re
from typing import Any

import requests
import urllib3
from bs4 import BeautifulSoup

from .config import ESMConfig
from .exceptions import (
    AuthenticationError,
    PasswordChangeRequiredError,
    PermissionDeniedError,
    SessionExpiredError,
    ValidationError,
)
from .selectors import get_selectors, get_url_patterns

# Suppress InsecureRequestWarning when SSL verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class ESMClient:
    """HTTP client for Ellucian Solution Manager.

    Handles authentication, session management, and response validation.
    All methods use centralized selectors and URL patterns for maintainability.

    Supports tunnel mode for SSH tunnels: when ESM_TUNNEL_URL is set, requests
    are sent to the local tunnel endpoint with the real hostname in the Host
    header. Redirect Location headers are rewritten to route through the tunnel.
    """

    def __init__(self, config: ESMConfig | None = None):
        """Initialize client with configuration.

        Args:
            config: ESMConfig instance. If None, loads from environment.
        """
        self.config = config or ESMConfig.from_env()
        self.session = requests.Session()
        self.session.verify = self.config.verify_ssl
        self.csrf_token: str | None = None

        # Load selectors for configured version
        self._selectors = get_selectors(self.config.esm_version)
        self._urls = get_url_patterns(self.config.esm_version)

        # Tunnel mode: set Host header and install redirect rewriter
        if self.config.is_tunnel:
            self.session.headers["Host"] = self.config.real_host
            self.session.hooks["response"].append(self._rewrite_redirects)

    def _rewrite_redirects(self, response: requests.Response, **kwargs) -> requests.Response:
        """Response hook that rewrites redirect Location headers for tunnel mode.

        When ESM redirects to its real hostname, rewrite to the local tunnel
        so requests can follow the redirect without DNS resolution.
        """
        if "Location" in response.headers:
            location = response.headers["Location"]
            rewritten = location.replace(
                self.config.real_origin,
                self.config.tunnel_url.rstrip("/"),
            )
            if rewritten != location:
                response.headers["Location"] = rewritten
        return response

    @property
    def base_url(self) -> str:
        """Base URL for requests. Uses tunnel URL if configured."""
        if self.config.is_tunnel:
            # Derive path from ESM_URL, prepend tunnel URL
            from urllib.parse import urlparse

            path = urlparse(self.config.base_url).path.rstrip("/")
            return f"{self.config.tunnel_url.rstrip('/')}{path}"
        return self.config.base_url.rstrip("/")

    def _check_response(self, response: requests.Response) -> None:
        """Validate response for common error conditions.

        Args:
            response: HTTP response to check

        Raises:
            SessionExpiredError: If redirected to login page
            PermissionDeniedError: If access denied message in body
            ValidationError: If response indicates an error state
        """
        # Check for login redirect (session expired)
        if "/login/" in response.url and self._urls["login_page"] not in response.request.url:
            raise SessionExpiredError("Session expired - redirected to login page")

        # Check for password change requirement
        if self._selectors["password_init_indicator"] in response.url:
            raise PasswordChangeRequiredError("Password change required - user must update password via browser first")

        # Check for access denied in response body
        if response.status_code == 200 and "Access Denied" in response.text:
            raise PermissionDeniedError("Access denied for this operation")

        # Check HTTP status codes
        if response.status_code == 403:
            raise PermissionDeniedError("HTTP 403: Access denied")
        if response.status_code == 404:
            raise ValidationError("HTTP 404: Resource not found")
        if response.status_code >= 400:
            raise ValidationError(f"HTTP {response.status_code}: Request failed")

    def _get(self, endpoint: str, params: dict | None = None) -> requests.Response:
        """Make GET request with response validation.

        Args:
            endpoint: URL path relative to base URL
            params: Query parameters

        Returns:
            Validated response
        """
        url = f"{self.base_url}{endpoint}"
        response = self.session.get(url, params=params, timeout=self.config.timeout)
        self._check_response(response)
        return response

    def _post(self, endpoint: str, data: dict | None = None, params: dict | None = None) -> requests.Response:
        """Make POST request with CSRF token and response validation.

        Args:
            endpoint: URL path relative to base URL
            data: Form data
            params: Query parameters

        Returns:
            Validated response
        """
        url = f"{self.base_url}{endpoint}"
        post_data = data.copy() if data else {}

        # Add CSRF token if we have one
        if self.csrf_token:
            post_data[self._selectors["csrf_form_field"]] = self.csrf_token

        response = self.session.post(
            url, data=post_data, params=params, timeout=self.config.timeout, allow_redirects=True
        )
        self._check_response(response)
        return response

    def _parse_table(self, soup: BeautifulSoup) -> list[dict[str, str]]:
        """Parse a simple-table into list of dicts.

        Args:
            soup: BeautifulSoup of page containing table

        Returns:
            List of row dicts with header keys
        """
        table = soup.select_one(self._selectors["data_table"])
        if not table:
            return []

        rows = table.find_all("tr")
        if not rows:
            return []

        # Extract headers
        headers = [th.get_text(strip=True) for th in rows[0].find_all("th")]
        if not headers:
            # Try first row as headers if no th elements
            headers = [td.get_text(strip=True) for td in rows[0].find_all("td")]
            rows = rows[1:]
        else:
            rows = rows[1:]

        # Parse data rows
        result = []
        for row in rows:
            cells = row.find_all("td")
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row_data[headers[i]] = cell.get_text(strip=True)
                    # Also capture target-url attribute if present
                    url_attr = cell.get(self._selectors["target_url_attr"])
                    if url_attr:
                        row_data[f"{headers[i]}_url"] = url_attr
            result.append(row_data)

        return result

    def login(self) -> bool:
        """Authenticate with ESM.

        Establishes session by:
        1. Getting initial page to obtain cookies
        2. Extracting CSRF token from cookie
        3. Submitting credentials
        4. Validating login success

        Returns:
            True if login succeeded

        Raises:
            AuthenticationError: If login fails
            PasswordChangeRequiredError: If password change is required
        """
        missing = self.config.validate()
        if missing:
            raise AuthenticationError(f"Missing configuration: {', '.join(missing)}")

        # Get initial page to establish session cookies
        init_url = f"{self.base_url}/"
        self.session.get(init_url, timeout=self.config.timeout)

        # Extract CSRF token from cookie
        self.csrf_token = self.session.cookies.get(self._selectors["csrf_cookie"])
        if not self.csrf_token:
            raise AuthenticationError("Failed to obtain CSRF token from initial request")

        # Submit login
        response = self._post(
            self._urls["login_submit"],
            data={
                "username": self.config.username,
                "password": self.config.password,
            },
        )

        # Check for successful redirect to admin main
        if self._selectors["login_success_indicator"] in response.url:
            return True

        raise AuthenticationError("Login failed - check credentials")

    def get_environments(self) -> list[dict[str, Any]]:
        """Fetch list of all environments.

        Returns:
            List of environment dicts with keys:
            - name: Environment name
            - status: Environment status
            - db_sid: Database SID
            - admin_ip: Admin IP address
            - gateway_ip: Gateway IP
            - domain: Domain name
        """
        response = self._get(self._urls["environments"])
        soup = BeautifulSoup(response.text, "lxml")
        table = soup.select_one(self._selectors["data_table"])

        if not table:
            return []

        # Build header-to-index map for resilient parsing
        header_row = table.find("tr")
        headers = [th.get_text(strip=True) for th in header_row.find_all("th")]
        col = {name: i for i, name in enumerate(headers)}

        envs = []
        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cells) > col.get("Environment Name", 99):
                envs.append(
                    {
                        "name": cells[col["Environment Name"]],
                        "status": cells[col["Status"]],
                        "db_sid": cells[col["DB SID"]],
                        "admin_ip": cells[col.get("Admin (Private) IP", col.get("Admin IP", 4))],
                        "gateway_ip": cells[col.get("Admin (Private) Gateway IP", col.get("Gateway IP", 5))],
                        "domain": cells[col.get("Public Domain", col.get("Domain", 6))],
                    }
                )
        return envs

    def get_environment(self, env_name: str) -> dict[str, Any]:
        """Fetch environment details.

        Args:
            env_name: Environment name

        Returns:
            Dict with environment details including available sections
        """
        response = self._get(self._urls["env_detail"], params={"envName": env_name})
        soup = BeautifulSoup(response.text, "lxml")

        result: dict[str, Any] = {"name": env_name}

        # Extract header
        header = soup.select_one(self._selectors["main_content_header"])
        if header:
            result["header"] = header.get_text(strip=True)

        # Extract available sections from nav links
        sections = set()
        for link in soup.select(self._selectors["env_nav_link"]):
            url = link.get("target-url", "")
            match = re.search(r"/adminEnv/(\w+)", url)
            if match:
                sections.add(match.group(1))
        result["sections"] = sorted(sections)

        return result

    def get_products(self, env_name: str) -> list[dict[str, Any]]:
        """Fetch installed products for an environment.

        Args:
            env_name: Environment name

        Returns:
            List of product dicts with keys:
            - name: Product name
            - type: Product type
            - application: Application name
            - installed_version: Currently installed version
            - available_version: Latest available version
            - target_version: Selected target version (if any)
            - product_id: Product identifier for API calls
        """
        response = self._get(self._urls["products"], params={"envName": env_name})
        soup = BeautifulSoup(response.text, "lxml")
        table = soup.select_one(self._selectors["data_table"])

        if not table:
            return []

        products = []
        rows = table.find_all("tr")[1:]  # Skip header
        product_id_pattern = re.compile(self._selectors["product_id_pattern"])

        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 5:
                continue

            # Extract productId from target-url attribute
            product_id = ""
            for cell in cells:
                url = cell.get(self._selectors["product_id_attr"], "")
                match = product_id_pattern.search(url)
                if match:
                    product_id = match.group(1)
                    break

            products.append(
                {
                    "name": cells[0].get_text(strip=True),
                    "type": cells[1].get_text(strip=True),
                    "application": cells[2].get_text(strip=True),
                    "installed_version": cells[3].get_text(strip=True),
                    "available_version": cells[4].get_text(strip=True),
                    "target_version": cells[5].get_text(strip=True) if len(cells) > 5 else "",
                    "product_id": product_id,
                }
            )
        return products

    def get_machines(self, env_name: str) -> list[dict[str, Any]]:
        """Fetch machines for an environment.

        Args:
            env_name: Environment name

        Returns:
            List of machine dicts with role, OS, hostnames, IPs
        """
        response = self._get(self._urls["machines"], params={"envName": env_name})
        soup = BeautifulSoup(response.text, "lxml")
        return self._parse_table(soup)

    def get_available_releases(
        self, env_name: str, product_id: str, app_name: str | None = None
    ) -> list[dict[str, Any]]:
        """Fetch available upgrades for a product.

        Args:
            env_name: Environment name
            product_id: Product identifier
            app_name: Application name (optional)

        Returns:
            List of release dicts with version and release_date
        """
        params: dict[str, str] = {"envName": env_name, "productId": product_id}
        if app_name:
            params["applicationName"] = app_name

        response = self._get(self._urls["available_releases"], params=params)
        soup = BeautifulSoup(response.text, "lxml")
        table = soup.select_one(self._selectors["data_table"])

        if not table:
            return []

        releases = []
        rows = table.find_all("tr")[1:]  # Skip header
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 4:
                # Get version from checkbox value if present
                checkbox = row.select_one(self._selectors["target_radio"])
                version = checkbox.get("value") if checkbox else cells[2].get_text(strip=True)

                releases.append(
                    {
                        "version": version,
                        "release_date": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                    }
                )
        return releases

    def get_upgrade_properties(self, env_name: str, product_id: str, version: str) -> list[dict[str, Any]]:
        """Fetch upgrade properties (checkboxes) for a release.

        Args:
            env_name: Environment name
            product_id: Product identifier
            version: Release version

        Returns:
            List of property dicts with id, checked, and label
        """
        params = {"envName": env_name, "productId": product_id, "relVersion": version}
        response = self._get(self._urls["upgrade_properties"], params=params)
        soup = BeautifulSoup(response.text, "lxml")

        properties = []
        checkboxes = soup.select(self._selectors["property_checkbox"])
        for cb in checkboxes:
            cb_id = cb.get("id", "")
            checked = cb.has_attr("checked")

            # Extract label from parent or sibling elements
            label = ""
            parent = cb.find_parent("div", class_="message")
            if parent:
                label = parent.get_text(strip=True)
                label = label.replace(cb_id, "").strip()

            properties.append(
                {
                    "id": cb_id,
                    "checked": checked,
                    "label": label[:100] if len(label) > 100 else label,
                }
            )
        return properties

    def get_job_status(self, env_name: str, install_id: str) -> dict[str, Any]:
        """Fetch upgrade job status.

        Args:
            env_name: Environment name
            install_id: Installation job ID

        Returns:
            Dict with job_name, status, and console output
        """
        params = {"envName": env_name, "installId": install_id}
        response = self._get(self._urls["upgrade_monitor"], params=params)
        soup = BeautifulSoup(response.text, "lxml")

        result: dict[str, Any] = {"env_name": env_name, "install_id": install_id}

        # Job name
        job_div = soup.select_one(self._selectors["dialog_title"])
        if job_div:
            result["job_name"] = job_div.get_text(strip=True).replace("Job Name:", "").strip()

        # Status from icon class
        if soup.select_one(self._selectors["job_status_in_progress"]):
            result["status"] = "In Progress"
        elif soup.select_one(self._selectors["job_status_completed"]):
            result["status"] = "Completed"
        elif soup.select_one(self._selectors["job_status_failed"]):
            result["status"] = "Failed"
        else:
            result["status"] = "Unknown"

        # Console output
        console = soup.select_one(self._selectors["job_console"])
        if console:
            result["console"] = console.get_text()

        return result
