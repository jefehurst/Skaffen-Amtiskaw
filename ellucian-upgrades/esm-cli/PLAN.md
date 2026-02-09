# ESM CLI Tool - Development Plan

## Overview

Create a command-line tool for interacting with Ellucian Solution Manager (ESM) via screen-scraping. ESM is a
Grails-based web application (running on Tomcat) that manages Banner higher education software deployments. The CLI will
automate common administrative tasks that currently require manual web browser interaction.

**Primary Pain Points to Solve**:

1. Clicking all checkboxes under "Upgrade Properties" - tedious and repetitive
2. Updating passwords in the credentials tab - repetitive stress
3. Full CRUD for all ESM entities - enables Ansible automation

**Target Repository**: Separate repository, not part of stibbons.

**End Goal**: CLI wrapped by Ansible modules for declarative ESM environment setup.

______________________________________________________________________

## CLI Command Structure

### Global Options

| Option              | Env Var          | Description                             |
| ------------------- | ---------------- | --------------------------------------- |
| `--cache-dir PATH`  | `ESM_CACHE_DIR`  | Override session/cache directory        |
| `--config-dir PATH` | `ESM_CONFIG_DIR` | Override config directory               |
| `--host NAME`       | `ESM_HOST`       | Select configured host                  |
| `--url URL`         | `ESM_URL`        | Direct URL (skip config lookup)         |
| `--user USER`       | `ESM_USER`       | Username                                |
| `--password`        | `ESM_PASSWORD`   | Password (prompt if flag without value) |
| `--insecure`        | `ESM_INSECURE=1` | Skip SSL verification                   |
| `--json`            | `ESM_JSON=1`     | JSON output                             |
| `--quiet`           | `ESM_QUIET=1`    | Minimal output                          |

### Session Management

| Command               | Description                              |
| --------------------- | ---------------------------------------- |
| `esm login`           | Force new login, save session            |
| `esm logout`          | Clear session file                       |
| `esm session`         | Show session status (age, last activity) |
| `esm session refresh` | Force session refresh                    |

### Environments (CRUD)

| Command                                | Description                 |
| -------------------------------------- | --------------------------- |
| `esm env list`                         | List all environments       |
| `esm env show ENVNAME`                 | Show environment details    |
| `esm env create ENVNAME [--json FILE]` | Create new environment      |
| `esm env update ENVNAME [--json FILE]` | Update environment settings |
| `esm env delete ENVNAME`               | Delete environment          |

### Credentials

| Command                                             | Description                  |
| --------------------------------------------------- | ---------------------------- |
| `esm creds show ENVNAME`                            | Show credentials (masked)    |
| `esm creds set ENVNAME --db-password XXX`           | Set database password        |
| `esm creds set ENVNAME --install-user-password XXX` | Set install user password    |
| `esm creds set ENVNAME --from-file FILE`            | Bulk set from JSON/YAML      |
| `esm creds test ENVNAME`                            | Test credential connectivity |

### Machines (CRUD)

| Command                                    | Description                  |
| ------------------------------------------ | ---------------------------- |
| `esm machine list ENVNAME`                 | List machines in environment |
| `esm machine show ENVNAME MACHINE`         | Show machine details         |
| `esm machine create ENVNAME [--json FILE]` | Add machine to environment   |
| `esm machine update ENVNAME MACHINE [...]` | Update machine config        |
| `esm machine delete ENVNAME MACHINE`       | Remove machine               |

### Products & Upgrades

| Command                                              | Description                                |
| ---------------------------------------------------- | ------------------------------------------ |
| `esm products ENVNAME`                               | Show installed vs available                |
| `esm releases sync`                                  | Download new releases ("Get New Releases") |
| `esm upgrade list ENVNAME`                           | List available upgrades                    |
| `esm upgrade show ENVNAME UPGRADE`                   | Show upgrade details & properties          |
| `esm upgrade props ENVNAME UPGRADE`                  | Show upgrade properties                    |
| `esm upgrade props ENVNAME UPGRADE --from-file FILE` | Set upgrade properties from JSON           |
| `esm upgrade props ENVNAME UPGRADE --template NAME`  | Apply property template                    |
| `esm upgrade props ENVNAME UPGRADE --copy-from ENV`  | Copy properties from another env           |
| `esm upgrade install ENVNAME UPGRADE`                | Run the upgrade                            |

### Upgrade Property Templates

| Template      | Description                            |
| ------------- | -------------------------------------- |
| `full`        | All options enabled                    |
| `db-only`     | Database scripts only, no forms/deploy |
| `forms-only`  | Compile forms only                     |
| `deploy-only` | WAR deployment only, no DB changes     |
| `minimal`     | Bare minimum for the upgrade           |

### Agents

| Command                          | Description                        |
| -------------------------------- | ---------------------------------- |
| `esm agent list ENVNAME`         | List agents (upgrade + deployment) |
| `esm agent show ENVNAME AGENT`   | Show agent details                 |
| `esm agent status ENVNAME`       | Show online/offline status         |
| `esm agent create ENVNAME [...]` | Define new agent in Jenkins        |
| `esm agent delete ENVNAME AGENT` | Remove agent definition            |

### Jobs

| Command                | Description             |
| ---------------------- | ----------------------- |
| `esm job list ENVNAME` | List recent jobs        |
| `esm job show JOBID`   | Show job status         |
| `esm job log JOBID`    | Show job console output |
| `esm job wait JOBID`   | Block until complete    |
| `esm job cancel JOBID` | Cancel running job      |

### Users (CRUD)

| Command                          | Description       |
| -------------------------------- | ----------------- |
| `esm user list`                  | List users        |
| `esm user show USERNAME`         | Show user details |
| `esm user create USERNAME [...]` | Create user       |
| `esm user update USERNAME [...]` | Update user       |
| `esm user delete USERNAME`       | Delete user       |
| `esm user password USERNAME`     | Set user password |

### System Settings

| Command                             | Description          |
| ----------------------------------- | -------------------- |
| `esm settings show`                 | Show system settings |
| `esm settings set KEY VALUE`        | Set a setting        |
| `esm settings set --from-file FILE` | Bulk set from JSON   |

______________________________________________________________________

## Session Management Architecture

ESM (Grails/Spring) uses server-side sessions. The CLI must maintain browser-like state.

### Storage Locations (XDG-compliant)

```
~/.cache/esm-cli/                    # Default, override with --cache-dir
└── sessions/
    └── esm.example.edu/
        ├── cookies.json             # Cookie jar
        └── state.json               # Navigation state, CSRF tokens

~/.config/esm-cli/
├── config.yaml                      # Hosts, preferences
└── credentials/                     # Keyring fallback
```

### Session File Structure

```json
{
  "cookies": {
    "JSESSIONID": "ABC123...",
    "GRAILS_REMEMBER_ME": "..."
  },
  "state": {
    "last_used": "2025-12-06T12:00:00Z",
    "csrf_token": "abc123",
    "current_context": {
      "environment_id": 5,
      "environment_name": "TEST1"
    },
    "cached_ids": {
      "environments": {"TEST1": 5, "PROD": 12}
    }
  }
}
```

### Parallel Execution (Ansible)

Each Ansible task uses isolated `--cache-dir` to avoid session conflicts:

```yaml
- name: Configure TEST1
  environment:
    ESM_CACHE_DIR: "{{ ansible_runner_temp }}/esm-{{ inventory_hostname }}"
  esm_environment:
    name: TEST1
```

**No file locking needed** - sequential CLI usage and isolated Ansible sessions.

### State Replay

Some ESM operations require navigation context. The CLI replays navigation:

```python
def ensure_environment_context(session, env_name):
    if session.state.current_environment == env_name:
        return
    # Navigate: Environments tab → click environment row
    session.get("/admin/environment/list")
    session.get(f"/admin/environment/show/{env_id}")
    session.state.current_environment = env_name
    session.save()
```

______________________________________________________________________

## Config File

```yaml
# ~/.config/esm-cli/config.yaml
default_host: esm.example.edu

hosts:
  esm.example.edu:
    url: https://esm.example.edu:8443
    username: admin
    verify_ssl: true
    session_timeout: 1200  # 20 min

  esm-dev.example.edu:
    url: https://esm-dev.example.edu:8443
    username: admin
    verify_ssl: false  # self-signed cert
```

______________________________________________________________________

## Data Structures

### Credentials JSON

```json
{
  "database": {
    "password": "xxx"
  },
  "install_user": {
    "username": "banner",
    "password": "xxx"
  },
  "oracle_user": {
    "password": "xxx"
  },
  "weblogic": {
    "user_config_file": "/home/oracle/wlcr/wlconfig.prop",
    "user_key_file": "/home/oracle/wlcr/wlkey.prop"
  }
}
```

### Upgrade Properties JSON

```json
{
  "run_inp_scripts": true,
  "compile_forms": true,
  "run_baseline_scripts": false,
  "deploy_admin": true,
  "deploy_self_service": true,
  "deploy_employee_self_service": false,
  "backup_before_upgrade": true
}
```

______________________________________________________________________

## Premortem Analysis

### Authentication & Session

| Risk                                          | Likelihood | Impact | Mitigation                                    |
| --------------------------------------------- | ---------- | ------ | --------------------------------------------- |
| Session expires mid-operation                 | High       | Medium | Detect login redirect, auto-reauth, retry     |
| CSRF tokens required for forms                | High       | High   | Parse and include tokens in all POST requests |
| Login fails silently (200 with error in body) | Medium     | High   | Parse response body, don't trust status code  |
| Password change forced on login               | Low        | High   | Detect prompt, error with clear message       |

### Screen Scraping Fragility

| Risk                                    | Likelihood | Impact   | Mitigation                                                   |
| --------------------------------------- | ---------- | -------- | ------------------------------------------------------------ |
| ESM upgrade changes HTML structure      | High       | Critical | Version-specific parsers; test against multiple ESM versions |
| Form field names change                 | Medium     | High     | Parse form dynamically rather than hardcode field names      |
| Hidden fields required for submission   | High       | High     | Always scrape full form, submit all fields                   |
| Different HTML for different user roles | Medium     | Medium   | Test with admin and non-admin accounts                       |

### Credentials & Security

| Risk                             | Likelihood | Impact   | Mitigation                                             |
| -------------------------------- | ---------- | -------- | ------------------------------------------------------ |
| Passwords in shell history       | High       | High     | Prompt for passwords; warn if `--password=XXX` used    |
| Passwords in process list        | High       | Medium   | Read from env var or prompt, not CLI arg               |
| Session cookie stolen from cache | Medium     | High     | Restrict file permissions (0600)                       |
| Accidental credential logging    | Medium     | Critical | Sanitize all log output; never log response bodies raw |

### ESM-Specific Gotchas

| Risk                                    | Likelihood | Impact | Mitigation                                           |
| --------------------------------------- | ---------- | ------ | ---------------------------------------------------- |
| Upgrade properties vary by upgrade type | High       | High   | Scrape available options dynamically, don't hardcode |
| Machine types have different fields     | High       | Medium | Type-specific parsers                                |
| Some fields only appear conditionally   | High       | Medium | Check for element existence before parsing           |
| Operations take long time (upgrades)    | High       | Medium | Async job model with polling; clear timeout handling |

### Ansible Integration

| Risk                                  | Likelihood | Impact | Mitigation                                                    |
| ------------------------------------- | ---------- | ------ | ------------------------------------------------------------- |
| Module timeout during long operations | High       | High   | Async/poll pattern for upgrades; quick return for config      |
| Idempotency hard to guarantee         | High       | Medium | Check current state before mutation; report changed/unchanged |
| Diff mode (--check)                   | Medium     | Medium | Implement dry-run for all mutations                           |

### Testing

| Risk                        | Likelihood | Impact | Mitigation                                                  |
| --------------------------- | ---------- | ------ | ----------------------------------------------------------- |
| No ESM instance for testing | High       | High   | Mock server with recorded responses; fixture files          |
| Fixtures become stale       | High       | Medium | Document ESM version for each fixture; refresh periodically |
| Can't test mutations safely | High       | Medium | Dedicated test ESM instance; or mock-only for writes        |

### Highest Priority Mitigations

1. **Version-aware parsers** - ESM HTML structure will change; plan for it
2. **Dynamic form parsing** - Never hardcode form fields; scrape them
3. **Credential hygiene** - No passwords in CLI args, logs, or process list
4. **Session recovery** - Auto-detect and recover from expired sessions
5. **Idempotent operations** - Check before mutate for Ansible compatibility

______________________________________________________________________

## Technical Decisions

| Decision          | Choice              | Rationale                             |
| ----------------- | ------------------- | ------------------------------------- |
| HTTP client       | `requests`          | Standard, well-tested, sync is fine   |
| HTML parser       | `beautifulsoup4`    | Handles messy HTML, mature            |
| Parser backend    | `lxml`              | Fast, reliable                        |
| CLI framework     | `click`             | Clean API, built-in help generation   |
| Config management | `pydantic-settings` | Type-safe, env var support            |
| Output formatting | `rich`              | Nice tables, colors, progress bars    |
| XDG paths         | `platformdirs`      | Cross-platform config/cache locations |
| Testing           | `pytest`            | Standard, good fixtures support       |
| HTTP mocking      | `responses`         | Mock requests library calls           |
| Type checking     | `mypy`              | Catch errors early                    |

______________________________________________________________________

## Project Structure

```
esm-cli/
├── pyproject.toml
├── README.md
├── src/
│   └── esm/
│       ├── __init__.py
│       ├── cli.py              # Click CLI entry point
│       ├── client.py           # HTTP session management
│       ├── session.py          # Session persistence (cookies, state)
│       ├── config.py           # Configuration handling
│       ├── models.py           # Data models (Environment, Product, etc.)
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── base.py         # Base parser utilities, form scraping
│       │   ├── auth.py         # Login page parsing
│       │   ├── environments.py # Environment list/details
│       │   ├── credentials.py  # Credentials tab parsing
│       │   ├── machines.py     # Machine config parsing
│       │   ├── products.py     # Products parsing
│       │   ├── upgrades.py     # Upgrade properties parsing
│       │   ├── agents.py       # Agent status parsing
│       │   ├── settings.py     # System settings parsing
│       │   └── users.py        # Users parsing
│       ├── commands/           # CLI command groups
│       │   ├── __init__.py
│       │   ├── env.py
│       │   ├── creds.py
│       │   ├── machine.py
│       │   ├── products.py
│       │   ├── upgrade.py
│       │   ├── agent.py
│       │   ├── job.py
│       │   ├── user.py
│       │   └── settings.py
│       ├── formatters/
│       │   ├── __init__.py
│       │   ├── table.py        # Rich table output
│       │   └── json.py         # JSON output
│       └── exceptions.py       # Custom exceptions
├── tests/
│   ├── conftest.py
│   ├── fixtures/               # Mock HTML files
│   │   ├── v24/                # ESM 24.x HTML samples
│   │   └── v23/                # ESM 23.x HTML samples
│   ├── unit/
│   │   ├── test_parsers.py
│   │   ├── test_session.py
│   │   ├── test_models.py
│   │   └── test_config.py
│   └── integration/
│       └── test_live_esm.py    # Requires ESM_TEST_URL env
├── ansible/                    # Future: Ansible modules
│   └── modules/
│       ├── esm_environment.py
│       ├── esm_credentials.py
│       ├── esm_machine.py
│       └── esm_upgrade.py
└── docs/
    └── page_analysis.md        # Notes on ESM page structures from HAR/XHR analysis
```

______________________________________________________________________

## Dependencies

```toml
[tool.poetry.dependencies]
python = "^3.11"
requests = "^2.31"
beautifulsoup4 = "^4.12"
lxml = "^5.0"
click = "^8.1"
rich = "^13.0"
pydantic = "^2.0"
pydantic-settings = "^2.0"
platformdirs = "^4.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-cov = "^4.0"
responses = "^0.25"
black = "^24.0"
mypy = "^1.8"
ruff = "^0.2"
types-beautifulsoup4 = "^4.12"
types-requests = "^2.31"
```

______________________________________________________________________

## Development Phases

### Phase 1: Foundation

- [ ] Project scaffolding (Poetry, pytest, ruff, mypy)
- [ ] Session management (cookies, state persistence)
- [ ] Configuration management (env vars, config file, CLI args)
- [ ] SSL certificate handling
- [ ] Basic error types and exceptions

### Phase 2: Authentication & Core Client

- [ ] Login/authentication flow
- [ ] Session expiry detection and auto-reauth
- [ ] CSRF token extraction
- [ ] Navigation state replay
- [ ] Generic form scraping utilities

### Phase 3: Read Operations

- [ ] Environment list/show
- [ ] Credentials show (masked)
- [ ] Machine list/show
- [ ] Products list
- [ ] Upgrade list/show/props
- [ ] Agent status
- [ ] User list/show
- [ ] System settings show

### Phase 4: Write Operations (The Hard Part)

- [ ] Credentials set (form submission)
- [ ] Upgrade props set (checkbox automation)
- [ ] Environment create/update/delete
- [ ] Machine create/update/delete
- [ ] User create/update/delete
- [ ] Settings update

### Phase 5: Jobs & Upgrades

- [ ] Job list/show/log
- [ ] Job wait (polling)
- [ ] Upgrade install (trigger + monitor)
- [ ] Releases sync

### Phase 6: Ansible Modules

- [ ] esm_environment module
- [ ] esm_credentials module
- [ ] esm_machine module
- [ ] esm_upgrade_props module
- [ ] esm_upgrade module (install)

______________________________________________________________________

## Ansible Integration Example

```yaml
# ansible playbook for ESM environment setup
- name: Configure ESM environment
  hosts: localhost
  tasks:
    - name: Create TEST2 environment
      esm_environment:
        name: TEST2
        state: present
        settings:
          banner_code_tree_path: /u01/banner
          admin_server_hostname: esm.example.edu

    - name: Set TEST2 credentials
      esm_credentials:
        environment: TEST2
        db_password: "{{ vault_db_password }}"
        install_user_password: "{{ vault_install_password }}"

    - name: Add JobSub machine
      esm_machine:
        environment: TEST2
        name: jobsub01
        type: JobSub
        hostname: jobsub01.example.edu

    - name: Set upgrade properties for Banner General
      esm_upgrade_props:
        environment: TEST2
        upgrade: "Banner General 9.19"
        properties:
          run_inp_scripts: true
          compile_forms: true
          deploy_self_service: true

    - name: Install upgrade
      esm_upgrade:
        environment: TEST2
        upgrade: "Banner General 9.19"
        wait: true
```

______________________________________________________________________

## Open Questions

1. **ESM API?** - Documentation suggests no public API; web scraping only
2. **Version compatibility** - Need fixtures from ESM 22.x, 23.x, 24.x
3. **Form field stability** - Are field names/IDs consistent across versions?

______________________________________________________________________

## Next Steps

1. **Capture HAR/XHR** from real ESM instance for key workflows
2. **Create repository** with Poetry project structure
3. **Implement session module** (cookies, state, XDG paths)
4. **Implement auth flow** with real HTML fixtures
5. **Build parsers** incrementally from captured HTML
6. **Test against live ESM** for each parser
