# Runner Support CLI

CLI and API client for Runner Technologies Support (CLEAN_Address vendor).

## Installation

```bash
cd runner-support
poetry install
```

## Usage

```bash
# Login to Runner support
poetry run runner-support login

# Check login status
poetry run runner-support status

# Search support articles
poetry run runner-support search "banner"
poetry run runner-support search "CLEAN_Address" --max 20

# Logout (clear saved session)
poetry run runner-support logout
```

## Configuration

Credentials should be set in `local.env` at the repository root:

```
RUNNER_SUPPORT_USER=your_email
RUNNER_SUPPORT_PW=your_password
```

Session cookies are persisted to `~/.config/stibbons/runner_cookies.json` to minimize re-authentication.

## API Client

```python
from runner_support.client import RunnerSupportClient

with RunnerSupportClient() as client:
    # Search returns list of results with title, type, url, desc
    results = client.search("banner", max_matches=10)
    for r in results:
        print(f"{r['type']}: {r['title']}")
        print(f"  {r['url']}")
```

## Authentication Flow

Runner Support uses Freshdesk with standard Rails session authentication:

1. **GET `/support/login`** - Get login page with `_helpkit_session` cookie and CSRF tokens
2. **POST `/support/login`** - Submit credentials with `authenticity_token`
3. **Success** - `user_credentials` cookie set for persistent auth

For AJAX requests after login, include `X-CSRF-Token` header from the `csrf-token` meta tag.
