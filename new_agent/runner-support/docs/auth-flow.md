# Runner Support Authentication Flow

Runner Technologies Support (support.runnertech.com) uses Freshdesk as their support platform with standard Rails
session-based authentication.

## Overview

Unlike Ellucian Support (which uses Okta SAML SSO), Runner Support has a simple username/password login:

1. Visit login page to get session cookie and CSRF token
2. POST credentials with CSRF token
3. Receive persistent `user_credentials` cookie

## Detailed Flow

### Step 1: GET Login Page

```
GET https://support.runnertech.com/support/login
```

**Response Sets Cookies:**

- `_helpkit_session` - Rails session cookie (required for all requests)
- `_x_w` - Tracking cookie

**Response HTML Contains:**

- `<input name="authenticity_token" value="...">` - CSRF token for form submission
- `<meta name="csrf-token" content="...">` - CSRF token for AJAX requests

### Step 2: POST Login

```
POST https://support.runnertech.com/support/login
Content-Type: application/x-www-form-urlencoded

utf8=✓
&authenticity_token=<token_from_form>
&user_session[email]=<email>
&user_session[password]=<password>
&user_session[remember_me]=1
&meta[enterprise_enabled]=false
```

**Required Headers:**

- `Origin: https://support.runnertech.com`
- `Referer: https://support.runnertech.com/support/login`
- `Content-Type: application/x-www-form-urlencoded`

**Success Response (302 redirect to /support/home):** Sets cookies:

- `user_credentials` - Long-lived auth token (expires ~90 days)
- `helpdesk_node_session` - Node session identifier
- Updated `_helpkit_session`

### Step 3: Authenticated Requests

For regular page requests, just include the cookies.

For AJAX requests (like search), also include:

```
X-CSRF-Token: <token_from_meta_tag>
X-Requested-With: XMLHttpRequest
Accept: application/json, text/javascript, */*; q=0.01
```

## Key Differences from Ellucian

| Aspect              | Runner (Freshdesk)         | Ellucian (ServiceNow + Okta) |
| ------------------- | -------------------------- | ---------------------------- |
| Auth Type           | Rails session + form login | Okta IDX + SAML SSO          |
| MFA                 | None observed              | Okta Verify push/TOTP        |
| Session Persistence | `user_credentials` cookie  | ServiceNow glide\_\* cookies |
| CSRF Protection     | Rails authenticity_token   | ServiceNow sysparm_ck        |
| Complexity          | Simple                     | Complex multi-step flow      |

## Cookies Reference

| Cookie                  | Domain                  | Purpose                      |
| ----------------------- | ----------------------- | ---------------------------- |
| `_helpkit_session`      | support.runnertech.com  | Rails session (encrypted)    |
| `user_credentials`      | support.runnertech.com  | Remember-me token (~90 days) |
| `helpdesk_node_session` | support.runnertech.com  | Node routing                 |
| `_x_w`                  | support.runnertech.com  | Tracking                     |
| `__cf_bm`               | .support.runnertech.com | Cloudflare bot management    |

## API Endpoints

### Search (AJAX)

```
GET https://support.runnertech.com/support/search?term=<query>&max_matches=10
Accept: application/json
X-CSRF-Token: <token>
X-Requested-With: XMLHttpRequest
```

**Response:**

```json
[
  {
    "title": "Article Title",
    "group": "Article",
    "desc": "Description snippet...",
    "type": "ARTICLE",
    "url": "/support/solutions/articles/5000123456"
  }
]
```

Result types: `ARTICLE`, `TICKET`, `ARCHIVED TICKET`
