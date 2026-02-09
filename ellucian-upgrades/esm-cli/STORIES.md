# ESM CLI - User Stories

This document defines all user stories for the ESM CLI tool. Each story maps to one or more HAR captures needed for
development.

______________________________________________________________________

## Story Index

| ID     | Category    | Story                                  | Priority |
| ------ | ----------- | -------------------------------------- | -------- |
| AUTH-1 | Auth        | Login to ESM                           | P0       |
| AUTH-2 | Auth        | Logout / clear session                 | P0       |
| AUTH-3 | Auth        | Handle session expiry                  | P0       |
| ENV-1  | Environment | List all environments                  | P0       |
| ENV-2  | Environment | Show environment details               | P0       |
| ENV-3  | Environment | Create new environment                 | P1       |
| ENV-4  | Environment | Update environment settings            | P1       |
| ENV-5  | Environment | Delete environment                     | P2       |
| CRED-1 | Credentials | Show credentials (masked)              | P0       |
| CRED-2 | Credentials | Set credentials (bulk)                 | P0       |
| CRED-3 | Credentials | Test credentials                       | P1       |
| MACH-1 | Machine     | List machines in environment           | P0       |
| MACH-2 | Machine     | Show machine details                   | P1       |
| MACH-3 | Machine     | Create machine                         | P1       |
| MACH-4 | Machine     | Update machine                         | P1       |
| MACH-5 | Machine     | Delete machine                         | P2       |
| PROD-1 | Products    | List products with versions            | P0       |
| REL-1  | Releases    | Sync releases ("Get New Releases")     | P1       |
| UPG-1  | Upgrade     | List available upgrades                | P0       |
| UPG-2  | Upgrade     | Show upgrade details                   | P0       |
| UPG-3  | Upgrade     | View upgrade properties                | P0       |
| UPG-4  | Upgrade     | Set upgrade properties (interactive)   | P0       |
| UPG-5  | Upgrade     | Set upgrade properties (batch/file)    | P1       |
| UPG-6  | Upgrade     | Install upgrade (run job)              | P0       |
| UPG-7  | Upgrade     | Select and configure batch of upgrades | P0       |
| AGT-1  | Agent       | List agents                            | DEFERRED |
| AGT-2  | Agent       | Show agent status                      | DEFERRED |
| AGT-3  | Agent       | Create agent                           | DEFERRED |
| AGT-4  | Agent       | Delete agent                           | DEFERRED |
| JOB-1  | Job         | List jobs for environment              | DEFERRED |
| JOB-2  | Job         | Show job status                        | P0       |
| JOB-3  | Job         | View job log                           | P0       |
| JOB-4  | Job         | Wait for job completion                | P0       |
| JOB-5  | Job         | Cancel job                             | P2       |
| USR-1  | User        | List users                             | P1       |
| USR-2  | User        | Show user                              | P1       |
| USR-3  | User        | Create user                            | P2       |
| USR-4  | User        | Update user                            | P2       |
| USR-5  | User        | Delete user                            | P2       |
| USR-6  | User        | Set user password                      | P2       |
| SET-1  | Settings    | Show system settings                   | P1       |
| SET-2  | Settings    | Update system settings                 | P2       |

______________________________________________________________________

## Detailed Stories

### AUTH-1: Login to ESM

**As a** CLI user **I want to** authenticate to ESM **So that** I can perform operations

**Acceptance Criteria**:

- [ ] Accept URL, username, password from CLI args, env vars, or config file
- [ ] Prompt for password if not provided (no echo)
- [ ] Store session cookies in cache directory
- [ ] Handle invalid credentials with clear error message
- [ ] Handle password-change-required prompt

**Sub-tasks**:

- [ ] Parse login form (find CSRF token, form fields)
- [ ] Submit login POST
- [ ] Detect success vs failure from response
- [ ] Persist cookies

**HAR Captures**: `auth-login-ok`, `auth-login-fail`, `auth-login-pwchange`

______________________________________________________________________

### AUTH-2: Logout / Clear Session

**As a** CLI user **I want to** clear my session **So that** credentials aren't persisted

**Acceptance Criteria**:

- [ ] Delete session files from cache directory
- [ ] Optionally hit ESM logout endpoint

**Sub-tasks**:

- [ ] Implement `esm logout` command
- [ ] Clear cookies.json and state.json

**HAR Captures**: `auth-logout`

______________________________________________________________________

### AUTH-3: Handle Session Expiry

**As a** CLI user **I want** session expiry to be handled automatically **So that** I don't get cryptic errors

**Acceptance Criteria**:

- [ ] Detect redirect to login page
- [ ] Re-authenticate automatically
- [ ] Retry the original request
- [ ] Fail gracefully if re-auth fails

**Sub-tasks**:

- [ ] Add session-check middleware to client
- [ ] Implement auto-reauth logic

**HAR Captures**: `auth-expired` (capture a request after session timeout)

______________________________________________________________________

### ENV-1: List All Environments

**As a** CLI user **I want to** see all configured environments **So that** I know what's available

**Acceptance Criteria**:

- [ ] Show environment names
- [ ] Show environment status (if visible)
- [ ] Support `--json` output

**Sub-tasks**:

- [ ] Navigate to environments page
- [ ] Parse environment list table
- [ ] Extract environment IDs for later use

**HAR Captures**: `env-list`

______________________________________________________________________

### ENV-2: Show Environment Details

**As a** CLI user **I want to** see details of a specific environment **So that** I understand its configuration

**Acceptance Criteria**:

- [ ] Show environment settings (paths, hostnames, etc.)
- [ ] Show associated machines
- [ ] Show agent status summary

**Sub-tasks**:

- [ ] Navigate to environment show page
- [ ] Parse Env Settings tab
- [ ] Parse Machines tab summary

**HAR Captures**: `env-show`

______________________________________________________________________

### ENV-3: Create New Environment

**As a** CLI user **I want to** create a new environment **So that** I can manage a new Banner instance

**Acceptance Criteria**:

- [ ] Accept environment name
- [ ] Accept initial settings (from JSON or flags)
- [ ] Report success/failure

**Sub-tasks**:

- [ ] Find "create environment" form
- [ ] Parse required fields
- [ ] Submit form
- [ ] Verify creation

**HAR Captures**: `env-create`

______________________________________________________________________

### ENV-4: Update Environment Settings

**As a** CLI user **I want to** modify environment settings **So that** I can change paths, hostnames, etc.

**Acceptance Criteria**:

- [ ] Accept settings from JSON file or flags
- [ ] Only update specified fields
- [ ] Report what changed

**Sub-tasks**:

- [ ] Navigate to Env Settings
- [ ] Parse current values
- [ ] Submit updated form
- [ ] Verify changes

**HAR Captures**: `env-update`

______________________________________________________________________

### ENV-5: Delete Environment

**As a** CLI user **I want to** remove an environment **So that** I can clean up obsolete configurations

**Acceptance Criteria**:

- [ ] Require confirmation (or `--force`)
- [ ] Report success/failure

**HAR Captures**: `env-delete`

______________________________________________________________________

### CRED-1: Show Credentials

**As a** CLI user **I want to** see what credentials are configured **So that** I know what's set up

**Acceptance Criteria**:

- [ ] Show credential fields (masked values)
- [ ] Show which fields are populated vs empty

**Sub-tasks**:

- [ ] Navigate to Credentials tab
- [ ] Parse form fields
- [ ] Identify populated vs empty

**HAR Captures**: `cred-show`

______________________________________________________________________

### CRED-2: Set Credentials (Bulk)

**As a** CLI user **I want to** set multiple credentials at once **So that** I don't have to click through the UI
repeatedly

**Acceptance Criteria**:

- [ ] Accept credentials from JSON file
- [ ] Set multiple passwords in one operation
- [ ] Report what was changed

**Sub-tasks**:

- [ ] Navigate to Credentials tab
- [ ] Parse form structure
- [ ] Fill in values
- [ ] Submit form
- [ ] Verify changes saved

**HAR Captures**: `cred-set`

______________________________________________________________________

### CRED-3: Test Credentials

**As a** CLI user **I want to** verify credentials work **So that** I catch errors before running upgrades

**Acceptance Criteria**:

- [ ] Trigger ESM's credential test (if available)
- [ ] Report pass/fail for each credential type

**HAR Captures**: `cred-test` (if ESM has this feature)

______________________________________________________________________

### MACH-1: List Machines

**As a** CLI user **I want to** see machines in an environment **So that** I understand the topology

**Acceptance Criteria**:

- [ ] Show machine names, types, hostnames
- [ ] Support `--json` output

**HAR Captures**: `mach-list`

______________________________________________________________________

### MACH-2: Show Machine Details

**As a** CLI user **I want to** see details of a specific machine **So that** I can review its configuration

**HAR Captures**: `mach-show`

______________________________________________________________________

### MACH-3: Create Machine

**As a** CLI user **I want to** add a machine to an environment **So that** I can configure new servers

**HAR Captures**: `mach-create-jobsub`, `mach-create-app` (different machine types have different forms)

______________________________________________________________________

### MACH-4: Update Machine

**As a** CLI user **I want to** modify a machine's configuration **So that** I can change hostnames, paths, etc.

**HAR Captures**: `mach-update`

______________________________________________________________________

### MACH-5: Delete Machine

**As a** CLI user **I want to** remove a machine **So that** I can clean up obsolete entries

**HAR Captures**: `mach-delete`

______________________________________________________________________

### PROD-1: List Products

**As a** CLI user **I want to** see installed products and versions **So that** I know what's deployed

**Acceptance Criteria**:

- [ ] Show product names
- [ ] Show installed version
- [ ] Show available version (if upgrade exists)

**Sub-tasks**:

- [ ] Navigate to Products tab
- [ ] Parse product table
- [ ] Extract version info

**HAR Captures**: `prod-list`

______________________________________________________________________

### REL-1: Sync Releases

**As a** CLI user **I want to** download new releases from Ellucian **So that** I have the latest upgrades available

**Acceptance Criteria**:

- [ ] Trigger "Get New Releases" action
- [ ] Report how many new releases found
- [ ] Handle Download Center credential errors

**HAR Captures**: `rel-sync`

______________________________________________________________________

### UPG-1: List Available Upgrades

**As a** CLI user **I want to** see what upgrades are available **So that** I can plan my upgrade path

**Acceptance Criteria**:

- [ ] List upgrades by product
- [ ] Show upgrade version/name
- [ ] Show if already selected

**HAR Captures**: `upg-list`

______________________________________________________________________

### UPG-2: Show Upgrade Details

**As a** CLI user **I want to** see details about an upgrade **So that** I understand what it includes

**HAR Captures**: `upg-show`

______________________________________________________________________

### UPG-3: View Upgrade Properties

**As a** CLI user **I want to** see the current upgrade properties **So that** I know what options are set

**Acceptance Criteria**:

- [ ] List all property fields
- [ ] Show current values (checkboxes, text fields, selects)
- [ ] Distinguish between different field types

**Sub-tasks**:

- [ ] Navigate to upgrade properties page
- [ ] Parse all form elements
- [ ] Categorize by type (checkbox, text, select)

**HAR Captures**: `upg-props-view`

______________________________________________________________________

### UPG-4: Set Upgrade Properties (Interactive)

**As a** CLI user **I want to** interactively set upgrade properties **So that** I can handle complex/unusual properties

**Acceptance Criteria**:

- [ ] Prompt for each property
- [ ] Show current value
- [ ] Accept y/n for checkboxes
- [ ] Accept text input for text fields
- [ ] Allow skipping (keep current value)
- [ ] Submit all changes at end

**Sub-tasks**:

- [ ] Parse properties form
- [ ] Build interactive prompt loop
- [ ] Handle checkbox properties
- [ ] Handle text input properties
- [ ] Handle select/dropdown properties
- [ ] Submit form

**HAR Captures**: `upg-props-set`

______________________________________________________________________

### UPG-5: Set Upgrade Properties (Batch)

**As a** CLI user **I want to** set upgrade properties from a file **So that** I can automate repeated configurations

**Acceptance Criteria**:

- [ ] Accept JSON/YAML file with property values
- [ ] Apply template presets (full, db-only, etc.)
- [ ] Copy properties from another environment
- [ ] Report what was changed

**HAR Captures**: (same as UPG-4)

______________________________________________________________________

### UPG-6: Install Upgrade

**As a** CLI user **I want to** trigger an upgrade installation **So that** the upgrade runs

**Acceptance Criteria**:

- [ ] Trigger upgrade job
- [ ] Return job ID
- [ ] Optionally wait for completion

**HAR Captures**: `upg-install`

______________________________________________________________________

### UPG-7: Select and Configure Batch of Upgrades

**As a** CLI user **I want to** select multiple upgrades and configure their properties **So that** I can set up a
complete upgrade run efficiently

This is the **primary workflow** the CLI is built to improve.

**Acceptance Criteria**:

- [ ] List available upgrades, allow multi-select
- [ ] For each selected upgrade, prompt through properties
- [ ] Allow skipping "known-safe" properties (future: auto-answer)
- [ ] Show summary before committing
- [ ] Handle varied property types:
  - Checkboxes (most common, usually skip-able)
  - Text inputs (paths, parameters - need attention)
  - Dropdowns (rare, need attention)

**Workflow**:

```
$ esm upgrade batch TEST1

Available upgrades for TEST1:
  [1] Banner General 9.19
  [2] Banner General 9.20
  [3] Banner Finance 9.13
  [4] Banner Student 9.23

Select upgrades (comma-separated, or 'all'): 1,3

Configuring: Banner General 9.19
  Run INP Scripts [Y/n]:
  Compile Forms [Y/n]:
  Custom SQL Path [/default/path]: /custom/path
  Deploy Self-Service [Y/n]: n
  ...

Configuring: Banner Finance 9.13
  Run INP Scripts [Y/n]:
  ...

Summary:
  Banner General 9.19 - 12 properties configured
  Banner Finance 9.13 - 8 properties configured

Proceed? [y/N]: y

Started job 4521: Banner General 9.19
Started job 4522: Banner Finance 9.13
```

**Sub-tasks**:

- [ ] Parse products page to find available upgrades
- [ ] Implement multi-select UI
- [ ] Loop through selected upgrades
- [ ] For each: navigate to properties, prompt, submit
- [ ] Track which upgrades succeeded/failed

**HAR Captures**: `upg-batch` (full workflow)

______________________________________________________________________

### AGT-1: List Agents

> **STATUS: DEFERRED** - No agent list endpoint found in ESM. Agent management may be done through machine configuration
> or not exposed via web UI.

**As a** CLI user **I want to** see configured agents **So that** I know what's set up

**HAR Captures**: `agt-list`

______________________________________________________________________

### AGT-2: Show Agent Status

> **STATUS: DEFERRED** - No agent status endpoint found in ESM.

**As a** CLI user **I want to** see if agents are online **So that** I know if upgrades can run

**HAR Captures**: `agt-status`

______________________________________________________________________

### AGT-3: Create Agent

> **STATUS: DEFERRED** - No agent management endpoints found.

**As a** CLI user **I want to** define a new agent **So that** I can add machines to the upgrade process

**HAR Captures**: `agt-create`

______________________________________________________________________

### AGT-4: Delete Agent

> **STATUS: DEFERRED** - No agent management endpoints found.

**As a** CLI user **I want to** remove an agent **So that** I can clean up obsolete entries

**HAR Captures**: `agt-delete`

______________________________________________________________________

### JOB-1: List Jobs

> **STATUS: DEFERRED** - No job list endpoint found in ESM. Jobs can only be monitored via `/adminEnv/upgradeMonitor`
> which requires an `installId` obtained when starting an upgrade job. Historical job listing not available.

**As a** CLI user **I want to** see recent jobs **So that** I can track upgrade history

**HAR Captures**: `job-list`

______________________________________________________________________

### JOB-2: Show Job Status

**As a** CLI user **I want to** see a job's current status **So that** I know if it's running/complete/failed

**HAR Captures**: `job-show`

______________________________________________________________________

### JOB-3: View Job Log

**As a** CLI user **I want to** see job output **So that** I can debug failures

**HAR Captures**: `job-log`

______________________________________________________________________

### JOB-4: Wait for Job Completion

**As a** CLI user **I want to** block until a job finishes **So that** I can script sequential operations

**Acceptance Criteria**:

- [ ] Poll job status
- [ ] Exit 0 on success, non-zero on failure
- [ ] Show progress indicator

**HAR Captures**: (uses JOB-2 repeatedly)

______________________________________________________________________

### JOB-5: Cancel Job

**As a** CLI user **I want to** cancel a running job **So that** I can stop a mistake

**HAR Captures**: `job-cancel`

______________________________________________________________________

### USR-1 through USR-6: User Management

Lower priority CRUD operations for user management.

**HAR Captures**: `usr-list`, `usr-show`, `usr-create`, `usr-update`, `usr-delete`, `usr-password`

______________________________________________________________________

### SET-1: Show System Settings

**As a** CLI user **I want to** see system settings **So that** I can review configuration

**HAR Captures**: `set-show`

______________________________________________________________________

### SET-2: Update System Settings

**As a** CLI user **I want to** modify system settings **So that** I can configure Download Center, Jenkins, etc.

**HAR Captures**: `set-update`

______________________________________________________________________

## Upgrade Properties Deep Dive

The upgrade properties form is the primary pain point. Properties come in several types:

### Property Types

| Type     | Example                   | Interactive Handling            |
| -------- | ------------------------- | ------------------------------- |
| Checkbox | "Run INP Scripts"         | Prompt `[Y/n]` or `[y/N]`       |
| Text     | "Custom SQL Path"         | Show current, prompt for new    |
| Select   | "Compile Target"          | Show options, prompt for choice |
| Hidden   | CSRF token, form metadata | Preserve automatically          |

### Common Properties (usually auto-answer)

These appear on most upgrades and rarely need changes:

- Run INP Scripts → usually Yes
- Compile Forms → usually Yes
- Run Baseline Scripts → usually No (only for fresh installs)
- Backup Before Upgrade → usually Yes

### Attention-Required Properties

These vary by upgrade and need user input:

- Custom paths (text input)
- Deployment targets (checkboxes for which apps to deploy)
- Database options (may have text inputs)

### Future: Auto-Answer Configuration

```yaml
# ~/.config/esm-cli/property-defaults.yaml
defaults:
  run_inp_scripts: true
  compile_forms: true
  backup_before_upgrade: true
  run_baseline_scripts: false

# Prompt for these even in batch mode
always_prompt:
  - custom_sql_path
  - deploy_*  # glob pattern
```

______________________________________________________________________

## Fixture Capture Methods

There are two methods to capture ESM fixtures for development:

1. **Manual HAR Capture** - Human uses browser DevTools
2. **Agent HTTP Exploration** - Claude agent with HTTP access explores ESM directly

______________________________________________________________________

## Method 1: Manual HAR Capture

### Prerequisites

1. Browser with DevTools (Chrome/Firefox/Edge)
2. Access to ESM instance
3. Test environment (not production)

### Capture Settings

1. Open DevTools → Network tab
2. Check "Preserve log"
3. Clear existing entries before starting
4. Perform the action
5. Right-click → "Save all as HAR with content"

### File Naming Convention

```
<story-id>.har

Examples:
auth-login-ok.har
env-list.har
upg-props-set.har
```

ESM version information is embedded in the HTML responses, so no need to encode it in filenames.

### Capture Checklist

Capture these in order (session builds on previous):

#### Session 1: Auth & Navigation

| Order | Story ID          | Action                             |
| ----- | ----------------- | ---------------------------------- |
| 1     | `auth-login-ok`   | Fresh login with valid credentials |
| 2     | `env-list`        | Click Environments tab             |
| 3     | `env-show`        | Click on an environment            |
| 4     | `auth-logout`     | Click logout                       |
| 5     | `auth-login-fail` | Login with wrong password          |

#### Session 2: Environment Details

| Order | Story ID     | Action                            |
| ----- | ------------ | --------------------------------- |
| 1     | (login)      | Login                             |
| 2     | `cred-show`  | Navigate to Credentials tab       |
| 3     | `cred-set`   | Change a password, save           |
| 4     | `mach-list`  | Navigate to Machines tab          |
| 5     | `mach-show`  | Click on a machine                |
| 6     | `prod-list`  | Navigate to Products tab          |
| 7     | `agt-list`   | Navigate to view agents           |
| 8     | `agt-status` | Check agent online/offline status |

#### Session 3: Upgrades (The Main Event)

| Order | Story ID         | Action                                 |
| ----- | ---------------- | -------------------------------------- |
| 1     | (login)          | Login                                  |
| 2     | `upg-list`       | Navigate to Products, expand a product |
| 3     | `upg-show`       | Click on an available upgrade          |
| 4     | `upg-props-view` | View upgrade properties form           |
| 5     | `upg-props-set`  | Change properties, save                |
| 6     | `upg-install`    | Click Install (capture the trigger)    |
| 7     | `job-list`       | View job list                          |
| 8     | `job-show`       | Click on running/completed job         |
| 9     | `job-log`        | View job console output                |

#### Session 4: Create/Delete Operations (if safe)

| Order | Story ID             | Action                  |
| ----- | -------------------- | ----------------------- |
| 1     | `env-create`         | Create test environment |
| 2     | `mach-create-jobsub` | Add JobSub machine      |
| 3     | `mach-create-app`    | Add App Server machine  |
| 4     | `mach-delete`        | Delete a machine        |
| 5     | `env-delete`         | Delete test environment |

#### Session 5: System & Users

| Order | Story ID   | Action               |
| ----- | ---------- | -------------------- |
| 1     | `set-show` | View System Settings |
| 2     | `usr-list` | View Users           |
| 3     | `usr-show` | Click on a user      |

### Sanitization

Before sharing HAR files:

1. **Remove/mask passwords** in request bodies
2. **Remove session cookies** if sharing publicly
3. **Keep CSRF tokens** - needed to understand form structure
4. **Keep response bodies** - needed for parser development

### Directory Structure

```
fixtures/
├── har/
│   ├── auth-login-ok.har
│   ├── auth-login-fail.har
│   ├── env-list.har
│   └── ...
└── html/
    ├── login-page.html
    ├── env-list.html
    └── ...
```

The `html/` directory contains extracted response bodies for unit tests.

______________________________________________________________________

## Method 2: Agent HTTP Exploration

A Claude agent with HTTP access (via MCP tool or WebFetch) can explore ESM directly, documenting page structures and
building fixtures without manual browser interaction.

### Prerequisites

1. Claude agent with HTTP/WebFetch capability
2. ESM URL, username, password provided by user
3. Test environment (not production)
4. Permission to make HTTP requests to ESM

### Agent Exploration Protocol

The agent should follow this protocol to systematically explore ESM:

#### Phase 1: Authentication Discovery

```
1. GET {base_url}/admin
   - Save response as: login-page.html
   - Document: form action, field names, CSRF token location

2. POST {base_url}/admin/login (or discovered action)
   - Body: username, password, CSRF token
   - Save response as: login-success.html or login-fail.html
   - Document: success indicators, redirect location, session cookies

3. Note session cookie names (JSESSIONID, etc.)
```

#### Phase 2: Navigation Discovery

With authenticated session:

```
4. GET {base_url}/admin/environment/list
   - Save as: env-list.html
   - Document: table structure, environment IDs, links

5. GET {base_url}/admin/environment/show/{id}
   - Save as: env-show.html
   - Document: tab structure, settings fields

6. For each tab (Credentials, Machines, Products, etc.):
   - GET the tab URL
   - Save response
   - Document form fields, table structures
```

#### Phase 3: Form Structure Analysis

For each form discovered:

```
- List all <input>, <select>, <textarea> elements
- Note: name, id, type, current value
- Identify hidden fields (CSRF, version tokens)
- Identify required vs optional fields
- Note any JavaScript-dependent behavior (document for manual verification)
```

#### Phase 4: Upgrade Properties Deep Dive

This is the critical path:

```
7. Navigate to Products tab
8. Find upgrade selection mechanism
9. GET upgrade properties page
   - Save as: upg-props-{product}.html
   - Document EVERY form field:
     - Checkboxes: name, id, checked state, label text
     - Text inputs: name, id, current value, label text
     - Selects: name, id, options, selected value
     - Hidden fields: name, value
10. Repeat for different upgrade types (General, Finance, Student, etc.)
    to capture variation in properties
```

### Agent Output Format

The agent should produce:

#### 1. Page Catalog (`fixtures/catalog.md`)

```markdown
# ESM Page Catalog

## Authentication
| URL Pattern | Method | Description | Fixture File |
|-------------|--------|-------------|--------------|
| /admin | GET | Login page | login-page.html |
| /admin/j_spring_security_check | POST | Login submit | - |

## Environments
| URL Pattern | Method | Description | Fixture File |
|-------------|--------|-------------|--------------|
| /admin/environment/list | GET | Environment list | env-list.html |
| /admin/environment/show/{id} | GET | Environment detail | env-show.html |

... etc
```

#### 2. Form Analysis (`fixtures/forms.md`)

```markdown
# ESM Form Analysis

## Login Form
- Action: /admin/j_spring_security_check
- Method: POST
- Fields:
  | Name | Type | Required | Notes |
  |------|------|----------|-------|
  | j_username | text | yes | |
  | j_password | password | yes | |
  | _csrf | hidden | yes | Token from page |

## Credentials Form
- Action: /admin/environment/credentials/save/{envId}
- Method: POST
- Fields:
  | Name | Type | Required | Notes |
  |------|------|----------|-------|
  | dbPassword | password | no | Database password |
  | installUserPassword | password | no | Install user |
  ...

## Upgrade Properties Form ({product})
- Action: /admin/upgrade/saveProperties/{upgradeId}
- Method: POST
- Fields:
  | Name | Type | Label | Default | Notes |
  |------|------|-------|---------|-------|
  | runInpScripts | checkbox | Run INP Scripts | checked | |
  | compileForms | checkbox | Compile Forms | checked | |
  | customSqlPath | text | Custom SQL Path | /u01/... | |
  ...
```

#### 3. HTML Fixtures (`fixtures/html/`)

Raw HTML responses for each page, sanitized:

- Passwords replaced with `[REDACTED]`
- Session tokens can remain (needed for structure analysis)
- Real environment names can remain or be replaced with TEST1, PROD, etc.

### Agent Exploration Commands

When the user provides ESM access, use prompts like:

```
Explore ESM at {url} with credentials {user}/{pass}.

Phase 1: Document the authentication flow
- Fetch the login page
- Identify form fields and CSRF token
- Attempt login
- Document success/failure indicators

Save findings to fixtures/catalog.md and fixtures/forms.md
Save HTML responses to fixtures/html/
```

```
Continue ESM exploration - Phase 2: Navigation

With the authenticated session:
- List all environments
- Show details for environment "{envname}"
- Document the tab structure and available pages

Update catalog.md and forms.md with findings
```

```
Continue ESM exploration - Phase 3: Upgrade Properties

Navigate to Products for environment "{envname}"
Find available upgrades
For each upgrade type, capture the properties form
Document EVERY field - this is the critical data

Focus on identifying:
- Which fields are checkboxes vs text vs select
- Which fields appear on all upgrades vs product-specific
- Default values
```

### Comparison: Manual vs Agent

| Aspect              | Manual HAR         | Agent Exploration          |
| ------------------- | ------------------ | -------------------------- |
| Setup               | Browser + DevTools | MCP/WebFetch access        |
| Speed               | Slower             | Faster                     |
| Completeness        | Human judgment     | Systematic                 |
| JavaScript handling | Full JS execution  | No JS (server-rendered OK) |
| Session management  | Automatic          | Must track cookies         |
| Documentation       | Separate step      | Inline with exploration    |
| Repeatability       | Manual each time   | Can re-run prompts         |

**Recommendation**: Use agent exploration for initial discovery and documentation, then manual HAR capture for any
JavaScript-heavy interactions or to verify agent findings.

______________________________________________________________________

## Implementation Order

Based on dependencies and priority:

### Phase 1: Foundation + Auth

1. AUTH-1 (login)
2. AUTH-2 (logout)
3. AUTH-3 (session expiry)

### Phase 2: Read Operations

4. ENV-1 (list environments)
5. ENV-2 (show environment)
6. MACH-1 (list machines)
7. PROD-1 (list products)
8. CRED-1 (show credentials) - **requires admin account**
9. ~~AGT-1, AGT-2 (list agents, status)~~ - **DEFERRED: no endpoint**

### Phase 3: Upgrade Workflow (The Core)

10. UPG-1 (list upgrades)
11. UPG-3 (view properties)
12. UPG-4 (set properties - interactive)
13. UPG-7 (batch workflow)
14. UPG-6 (install upgrade)
15. ~~JOB-1~~, JOB-2, JOB-3, JOB-4 (job management) - **JOB-1 DEFERRED: no list endpoint**

### Phase 4: Write Operations

16. CRED-2 (set credentials)
17. ENV-3, ENV-4 (create/update environment)
18. MACH-3, MACH-4 (create/update machine)
19. UPG-5 (batch properties from file)

### Phase 5: Cleanup Operations

20. ENV-5 (delete environment)
21. MACH-5 (delete machine)
22. JOB-5 (cancel job)

### Phase 6: Lower Priority

23. USR-\* (user management)
24. SET-\* (system settings)
25. AGT-3, AGT-4 (create/delete agents)
26. REL-1 (sync releases)
