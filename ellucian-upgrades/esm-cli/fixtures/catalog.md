# ESM Page Catalog

Reference for ESM CLI development. Generated from HAR analysis, December 2025.

## Base URL

```
https://<esm-host>:8081/admin
```

## Authentication

### Login Flow

1. `GET /login/auth` → Login form
2. `POST /login/authenticate` → Authenticate
3. `GET /` → Redirect to dashboard
4. `GET /adminMain/adminMain` → Dashboard

**Login Form Fields:**

| Field    | Type     | Notes                  |
| -------- | -------- | ---------------------- |
| username | text     |                        |
| password | password |                        |
| \_csrf   | hidden   | From XSRF-TOKEN cookie |

**Session Cookies:**

- `JSESSIONID` - Server session (replaced after login)
- `XSRF-TOKEN` - CSRF protection token

**CSRF Handling:**

- Token in cookie: `XSRF-TOKEN`
- Token in form: `_csrf` hidden field
- Token in header: `X-XSRF-TOKEN`
- Token also in `<meta name="_csrf">` on pages

### Logout

```
POST /logout/index
  _csrf: <token>
```

______________________________________________________________________

## Environments

### List Environments

```
GET /adminMain/environments
```

Returns HTML fragment with environment list.

### Show Environment

```
GET /adminEnv/adminEnv?envName=<name>
```

Returns environment details page with tabs.

______________________________________________________________________

## Products (Installed Versions)

### List Products

```
GET /adminEnv/products?envName=<name>
```

Returns table of installed products with:

- Product name and ID
- Installed version
- Target version (if selected)
- Application name

______________________________________________________________________

## Upgrades

### Available Releases

```
GET /adminEnv/availableReleases?envName=<name>&productId=<id>&applicationName=<app>
```

Shows available upgrades for a product. Table structure:

| Column             | Content                                     |
| ------------------ | ------------------------------------------- |
| Target Release     | Checkbox with `name="targetRadioSelection"` |
| Rel Doc            | Button to release docs                      |
| Available Upgrade  | Version number                              |
| Release Date       | Timestamp                                   |
| Upgrade Properties | Check/link icon                             |

**Target Selection:**

```
POST /adminEnv/selectTarget?envName=<name>&productId=<id>&applicationName=<app>
  targetRadioSelection: <version>
```

### Upgrade Properties

```
GET /adminEnv/upgradeSpecificProperties?envName=<name>&relVersion=<ver>&productId=<id>
```

Returns form with checkboxes for each property section.

**Checkbox Structure:**

```html
<input type="checkbox"
       name="adminEnvUpgradeSpecificSections"
       id="banner.pay83201u.overview">
```

- Each checkbox has a unique `id` (e.g., `banner.pay83201u.overview`)
- All share `name="adminEnvUpgradeSpecificSections"`
- Followed by descriptive text (not in label, just text after checkbox)

**Save Properties:**

```
POST /adminEnv/saveUpgradeSpecificProperties?envName=<name>&relVersion=<ver>&productId=<id>
  upgradeProperties: (empty)
  upgradeSectionStatuses: banner.pay83201u.overview=true,banner.pay83201u.self-service=true,
```

Note: `upgradeSectionStatuses` is a comma-separated list of `id=boolean` pairs.

### Manage Upgrade Job

```
POST /adminEnv/installReleasesPrompt?envName=<name>
```

Shows job configuration page with:

- Description text field (`id="adminEnvUpgradeEnvDescFld"`)
- Auto-Start Jobs checkbox (`name="adminEnvUpgradeEnvAutoStartJenkinsJobsFld"`, default CHECKED)
- Table of selected releases
- Table of pre-requisite releases (if any)

**Selected/Prerequisite Release Table:**

| Column             | Content                               |
| ------------------ | ------------------------------------- |
| Rel Doc            | Button to release docs                |
| Product            | Product name                          |
| Release Version    | Version number                        |
| Release Date       | Timestamp                             |
| Upgrade Properties | Check icon (green=done, link=pending) |
| Missing Files      | Warning if files missing              |

### Start Upgrade

```
POST /adminEnv/installReleases?envName=<name>
  upgradeEnvDesc: <description>
  autoStartJenkinsJobs: true|false
```

Returns redirect to upgrade monitor.

______________________________________________________________________

## Jobs

### Upgrade Monitor

```
GET /adminEnv/upgradeMonitor?envName=<name>&installId=<id>
```

Full page (not fragment) with auto-refresh. Shows:

- Job name: `<env>_instJob_<id>_InstallSoftware`
- Status: In Progress / Completed / Failed (icon-based)
- Start time
- Duration
- Console log (in `<pre id="out">`)

**Status Icons:**

- `.icon-in-progress` - Running
- `.icon-completed` - Success (presumed, check job-complete.har)
- `.icon-failed` - Failed (presumed)

**Auto-Refresh:**

- Default 30 seconds
- Controlled by `#jobMonitorRefreshIntervalFld`
- Triggers click on `#admin-main-job-monitor-refresh`

______________________________________________________________________

## URL Patterns

All URLs use query parameters, no REST-style paths:

```
/adminEnv/<action>?envName=<name>&param=value
```

Common parameters:

- `envName` - Environment name (required for most)
- `productId` - Product identifier (e.g., `BNR_GEN`, `BNR_HRPAY`)
- `applicationName` - Application name (e.g., `dev-db`)
- `relVersion` - Release version
- `_=<timestamp>` - Cache buster (auto-added by AJAX)

______________________________________________________________________

## Key Identifiers

### Product IDs (observed)

| ID         | Name                       |
| ---------- | -------------------------- |
| BNR_GEN    | Banner General             |
| BNR_AR     | Banner Accounts Receivable |
| BNR_HRPAY  | Banner HR and Payroll      |
| BNR_POSCTL | Banner Position Control    |

### CSS Classes

| Class                                    | Purpose                         |
| ---------------------------------------- | ------------------------------- |
| `.admin-main-nav-node`                   | Navigation button               |
| `.admin-env-upgrade-props-node`          | Upgrade properties button       |
| `.admin-env-target-radio-select`         | Target version checkbox         |
| `.admin-env-install-releases`            | Start upgrade button            |
| `.admin-env-save-upgrade-properties-btn` | Save/Reset/Cancel buttons       |
| `.doc-link`                              | Release documentation link      |
| `.doc-check-link`                        | Properties check icon (pending) |

______________________________________________________________________

## JavaScript Integration

ESM uses jQuery and custom `app.*` methods. Key patterns:

**Button Actions:** Buttons don't use standard form submission. They have `target-url` attributes:

```html
<button class="admin-env-save-upgrade-properties-btn"
        target-url="/admin/adminEnv/saveUpgradeSpecificProperties?...">
OK
</button>
```

JavaScript intercepts clicks and performs AJAX requests.

**Page Loading:** Content is loaded into `#main` div via AJAX. Full page reloads are rare.

______________________________________________________________________

## Machines

### List Machines

```
GET /adminEnv/machines?envName=<name>
```

Returns table with:

| Column                    | Content           |
| ------------------------- | ----------------- |
| Machine Role              | DB, Jobsub, App   |
| Machine OS                | Unix, Windows     |
| Admin (Private) Host Name | Internal hostname |
| Admin (Private) IP        | Internal IP       |
| Public Host Name          | External hostname |
| Public IP                 | External IP       |

______________________________________________________________________

## Environment Navigation

The environment detail page (`/adminEnv/adminEnv`) provides navigation to sub-pages:

| Section      | Endpoint                | Description              |
| ------------ | ----------------------- | ------------------------ |
| Products     | `/adminEnv/products`    | Installed products       |
| Upgrades     | `/adminEnv/installs`    | Upgrade history          |
| Deployments  | `/adminEnv/deployments` | Deployment status        |
| Env Settings | `/adminEnv/settings`    | Environment config       |
| Applications | `/adminEnv/servers`     | Application servers      |
| App Servers  | `/adminEnv/appservers`  | App server config        |
| Machines     | `/adminEnv/machines`    | Machine inventory        |
| Credentials  | `/adminEnv/credentials` | Credentials (admin only) |

______________________________________________________________________

## Live API Testing Results (December 2025)

Tested against Rio Hondo PLAS environment with `readonly` user.

### Working Endpoints

| Endpoint                              | Status | Notes                      |
| ------------------------------------- | ------ | -------------------------- |
| `/adminMain/environments`             | ✓      | Lists 5 environments       |
| `/adminEnv/adminEnv`                  | ✓      | Shows nav to sub-pages     |
| `/adminEnv/products`                  | ✓      | 64 products with versions  |
| `/adminEnv/machines`                  | ✓      | 14 machines with roles/IPs |
| `/adminEnv/availableReleases`         | ✓      | Version list per product   |
| `/adminEnv/upgradeSpecificProperties` | ✓      | Checkbox IDs and states    |

### Permission-Restricted Endpoints

| Endpoint                | Status        | Notes                        |
| ----------------------- | ------------- | ---------------------------- |
| `/adminEnv/credentials` | Access Denied | Requires admin-level account |

### Endpoints Not Found

| Endpoint           | Notes                                    |
| ------------------ | ---------------------------------------- |
| `/adminEnv/agents` | No agent management in ESM nav           |
| `/adminEnv/jobs`   | No job list - only monitor with known ID |

### Session Notes

- Must hit `/admin/` first to get both `JSESSIONID` and `XSRF-TOKEN`
- `source local.env` doesn't export vars - use `set -a && source && set +a`
- New users may hit `/login/initializeUserPrompt` (password change required)

______________________________________________________________________

## HAR Capture Status

### Captured (15 files)

Covers: login, environment list/show, products, upgrade workflow (select → properties → install → monitor)

### Still Needed for Full CRUD

| Category    | What's Missing                   |
| ----------- | -------------------------------- |
| Credentials | View/edit with admin account     |
| Environment | Create/edit forms                |
| Machine     | Create/edit forms                |
| Settings    | Environment settings form        |
| Servers     | Application server configuration |

______________________________________________________________________

## Scraping Strategy

1. **Session Management:**

   - Hit `/admin/` first to establish both cookies
   - Preserve both `JSESSIONID` and `XSRF-TOKEN` cookies
   - Extract CSRF token from cookie or `<meta name="_csrf">`
   - Include in forms as `_csrf` and in headers as `X-XSRF-TOKEN`

2. **Content Extraction:**

   - Parse HTML fragments (most responses are not full pages)
   - Use CSS selectors matching the documented classes
   - Extract data from tables with `.simple-table`
   - Product IDs are in `target-url` attributes on `<td>` cells

3. **Form Submission:**

   - Extract `target-url` from buttons
   - Build POST data from form fields
   - Handle redirects (302 responses)

4. **Upgrade Property Automation:**

   - Find all `input[name="adminEnvUpgradeSpecificSections"]`
   - Build `upgradeSectionStatuses` from checkbox IDs
   - Format: `id1=true,id2=true,`
