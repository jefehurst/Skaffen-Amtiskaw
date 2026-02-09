# Ellucian Support Center Client

CLI and API client for Ellucian's Support Center (ServiceNow-based) and Download Center (FlexNet).

## Features

- Okta SSO authentication with MFA support
- Session persistence to minimize re-authentication
- Knowledge base article search and retrieval
- Support ticket listing and commenting
- **Download Center**: Search and download software from FlexNet Operations

## Installation

```bash
cd ellucian-support
poetry install
```

## Configuration

Set credentials in environment or `local.env`:

```bash
ELLUCIAN_SUPPORT_USER=your_username
ELLUCIAN_SUPPORT_PW=your_password
```

## Usage

### CLI

```bash
# Login (reads MFA code from stdin - can be piped)
echo "123456" | poetry run ellucian-support login
poetry run ellucian-support login --force  # force re-auth

# Check session status
poetry run ellucian-support status

# Clear session
poetry run ellucian-support logout
```

### Knowledge Base Search

```bash
# General search
poetry run ellucian-support find "banner upgrade error"

# Filter by source: kb, docs, defect, release, idea, community
poetry run ellucian-support find "ODS materialized view" -s kb

# Filter by type: html, pdf, kb
poetry run ellucian-support find "installation guide" -t pdf

# Control result count
poetry run ellucian-support find "ORA-01400" -s kb -n 20

# JSON output
poetry run ellucian-support find "SFRPCHG" -s kb -j
```

### Fetching Articles

```bash
# Fetch by sys_id (from search result URLs, NOT article number)
poetry run ellucian-support fetch d675b57b877f3d9099ecca65dabb35a0

# List attachments
poetry run ellucian-support fetch d675b57b877f3d9099ecca65dabb35a0 -a
```

**IMPORTANT**: The `fetch` command takes a **sys_id** (the hex string from the URL), NOT the article number (e.g.,
000038387). Extract the sys_id from the search result URL:

```
URL: ...kb_knowledge.do?sys_id=d675b57b877f3d9099ecca65dabb35a0
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                Use this sys_id with fetch
```

### Support Tickets

```bash
# List recent tickets
poetry run ellucian-support tickets

# Get a specific ticket
poetry run ellucian-support ticket CSC03686271

# Add a comment
poetry run ellucian-support comment CSC03686271 "Update text here"
```

### Download Center

```bash
# List all available products
poetry run ellucian-support download products

# Search for products
poetry run ellucian-support download products -q ethos

# List files for a product (by line ID)
poetry run ellucian-support download files "Ellucian-Ethos-Identity"

# Filter files by pattern
poetry run ellucian-support download files "Ellucian-Ethos-Identity" -p "5.10"

# Download files (dry run)
poetry run ellucian-support download get "Ellucian-Ethos-Identity" -p "5.10" -n

# Download files to a directory
poetry run ellucian-support download get "Ellucian-Ethos-Identity" -p "baseline-5.10.0" -o ./downloads
```

### Python API

```python
from ellucian_support import EllucianClient

with EllucianClient() as client:
    # Authenticates automatically, prompts for MFA if needed
    response = client.get("/customer_center?id=customer_center_home")
```

## Session Persistence

Sessions are saved to `~/.config/stibbons/ellucian_cookies.json` and reused until they expire. This minimizes MFA
prompts.
