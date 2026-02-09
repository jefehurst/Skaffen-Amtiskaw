# Okta IDX Authentication Reverse Engineering Notes

> **Status**: Authentication flow works through MFA. SAML callback to ServiceNow still redirects to logout instead of
> establishing session. Rate-limited during debugging - needs further investigation.

This document captures key findings from reverse-engineering the Okta Identity Engine (IDX) authentication flow for
ServiceNow SSO integration.

## Overview

Ellucian Support uses ServiceNow with Okta SAML SSO. The authentication flow is:

1. ServiceNow redirects to Okta SAML endpoint
2. Okta presents login widget powered by IDX API
3. User submits credentials via IDX `/identify` endpoint
4. MFA challenge via IDX `/challenge/answer` endpoint
5. **Use `success.href` URL** from challenge response (contains short stateToken)
6. Token redirect provides SAML assertion in auto-submit form
7. Submit SAML assertion to ServiceNow `/nav_to.do`

## Critical Finding #1: stateToken Unicode Escapes

**The Problem**: The Okta login page embeds a `stateToken` in JavaScript that appears as a base64-like string. When
extracted naively and sent to `/idp/idx/introspect`, it returns:

```json
{"messages": [{"message": "The session has expired.", "i18n": {"key": "idx.session.expired"}, "class": "ERROR"}]}
```

Despite correct cookies, headers, and timing.

**The Root Cause**: The stateToken in the HTML is **escaped with hex character codes**. For example, dashes (`-`) are
encoded as `\x2D`:

```
Page token:       ...HVIOO\x2D9DzJTaLvdRHB3YTv...
Browser sends:    ...HVIOO-9DzJTaLvdRHB3YTv...
```

The page token is **5505 characters** but the correctly decoded token is **5301 characters** (204 character difference
from all the escape sequences).

**The Fix**: Decode the token with `codecs.decode(token, "unicode_escape")`:

```python
import codecs
import re

def extract_state_token(html: str) -> str | None:
    match = re.search(r'"stateToken"\s*:\s*"([^"]+)"', html)
    if match:
        # CRITICAL: Decode unicode escapes like \x2D -> -
        token = codecs.decode(match.group(1), "unicode_escape")
        return token
    return None
```

## Critical Finding #2: Success URL vs stateHandle

**The Problem**: After successful MFA, the `/challenge/answer` response contains both a `stateHandle` (1500+ chars) and
a `success` object with an `href` containing a short stateToken (46 chars).

**Wrong approach** (causes invalid SAML):

```python
state_handle = challenge_data.get("stateHandle")  # 1500 chars
redirect_url = f"/login/token/redirect?stateToken={state_handle}"
```

**Correct approach**:

```python
success_url = challenge_data.get("success", {}).get("href")
# e.g., "https://sso.ellucian.com/login/token/redirect?stateToken=02.id.XeQKj8p..."
```

The `success.href` URL contains the correct short stateToken that produces a valid SAML assertion.

## IDX API Headers

The Okta signin widget sends specific headers that should be matched:

```python
headers = {
    "Accept": "application/ion+json; okta-version=1.0.0",
    "Content-Type": "application/ion+json; okta-version=1.0.0",
    "Origin": "https://sso.ellucian.com",
    "X-Okta-User-Agent-Extended": "okta-auth-js/7.14.0 okta-signin-widget-7.37.1",
}
```

The `X-Okta-User-Agent-Extended` header identifies the client library version. While not strictly required for
authentication to work, it's good practice to match.

## IDX Flow Endpoints

| Endpoint                               | Purpose                                |
| -------------------------------------- | -------------------------------------- |
| `/idp/idx/introspect`                  | Exchange stateToken for stateHandle    |
| `/idp/idx/identify`                    | Submit username + password             |
| `/idp/idx/challenge`                   | Select MFA authenticator (if multiple) |
| `/idp/idx/challenge/answer`            | Submit MFA code                        |
| `/login/token/redirect?stateToken=...` | Get SAML assertion (use success.href)  |

## Cookies

The Okta page sets several cookies, but only these are required for IDX:

- `JSESSIONID` - Server session identifier
- `DT` - Unknown purpose, but sent by browser

Other cookies like `xids`, `sid`, `t` are cleared (set to empty with past expiry).

## MFA Handling

After `/identify`, if MFA is required the response contains:

```json
{
  "remediation": {
    "value": [
      {"name": "challenge-authenticator", "href": ".../challenge/answer"},
      {"name": "select-authenticator-authenticate", "href": ".../challenge"}
    ]
  },
  "authenticators": {
    "value": [{"type": "app", "displayName": "Google Authenticator", ...}]
  }
}
```

With only one authenticator (Google Authenticator), you can go directly to `/challenge/answer` without calling
`/challenge` first.

After successful MFA (`/challenge/answer`), the response includes:

```json
{
  "success": {
    "name": "success-redirect",
    "href": "https://sso.ellucian.com/login/token/redirect?stateToken=02.id.XeQKj8p..."
  },
  "stateHandle": "02.id.XeQKj8p...~c.pbuYn8SJ..."  // DO NOT USE THIS
}
```

**Always use the `success.href` URL directly** - do not construct your own URL with the stateHandle.

## SAML Callback to ServiceNow

The token redirect page contains an auto-submit form:

```html
<form method="post" action="https://elluciansupport.service-now.com/nav_to.do">
  <input type="hidden" name="SAMLResponse" value="PD94bWw..."/>
  <input type="hidden" name="RelayState" value="https://elluciansupport.service-now.com/customer_center?id=customer_center_home"/>
</form>
```

Browser sends these headers with the SAML POST:

```python
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://sso.ellucian.com",
    "Referer": "https://sso.ellucian.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
}
```

### Outstanding Issue

Despite correct SAML response and headers, ServiceNow redirects to `/auth_redirect.do?sysparm_url=logout_success.do`
instead of the customer portal. The browser HAR shows a successful redirect to
`customer_center?id=customer_center_home`.

**What we've verified works:**

- JSESSIONID remains consistent throughout the flow ✓
- RelayState is correctly set to `customer_center?id=customer_center_home` ✓
- All cookies match browser (BIGipServerpool, JSESSIONID, glide_user_route, glide_node_id_for_js) ✓
- Server accepts SAML and sets `glide_user` and `glide_user_session` cookies ✓
- Success URL from challenge/answer is used (short stateToken) ✓

**Critical finding: HTML encoding in SAML form (BOTH fields!)**

The token redirect page contains a form with HTML-encoded values. **BOTH** SAMLResponse and RelayState contain HTML
entities that must be decoded:

```html
<input name="SAMLResponse" value="PD94bWwg...&#x2B;..."/>
<input name="RelayState" value="https&#x3a;&#x2f;&#x2f;..."/>
```

The SAMLResponse contains `&#x2B;` for `+` characters (among others). If not decoded, the base64 is malformed and
ServiceNow rejects the assertion with a redirect to `logout_success.do`.

**Must decode BOTH with `html.unescape()`**:

```python
import html
saml_response = html.unescape(saml_response)  # CRITICAL - contains &#x2B; for +
relay_state = html.unescape(relay_state)      # Contains &#x3a; for : etc.
```

Quick test to verify:

```python
import base64
# If this fails, you forgot to html.unescape() the SAMLResponse
base64.b64decode(saml_response)
```

**Critical finding: RelayState origin**

The RelayState is embedded in the SAMLRequest URL when SSO is initiated. If you go directly to `login_with_sso.do`, the
RelayState defaults to `nav_to.do`. To get the correct RelayState (`customer_center?id=customer_center_home`), you must:

1. First visit the target page (e.g., `customer_center?id=customer_center_home`)
2. Then initiate SSO with: `login_with_sso.do?glide_sso_id=XXX&sysparm_url=<target_url>`

**SAML Request/Response binding**

ServiceNow generates a unique request ID (e.g., `SNC0b0ac9e58a36dbbf906987d9dcf0f107`) in the SAMLRequest. Okta echoes
this back in the SAMLResponse's `InResponseTo` attribute. ServiceNow validates this to prevent replay attacks.

The ID is stored server-side, tied to the JSESSIONID. If the session changes between request and response, validation
fails.

**Remaining theories to investigate:**

- SAML signature validation (certificate mismatch?)
- Timing issue with SAML assertion validity period
- Some server-side state not captured in cookies
- ServiceNow-specific SAML processing quirk

## Rate Limiting

Okta enforces rate limits on authentication endpoints. After several failed attempts, you may receive HTTP 429. Wait
before retrying to avoid account lockout.

## Debugging Tips

1. **HAR files are essential** - Capture a full browser login with network tools
2. **Compare token lengths** - If your token is longer than what browser sends, check for encoding
3. **Raw Set-Cookie headers** - httpx handles multi-value cookies correctly, but verify with
   `response.headers.multi_items()`
4. **Session timing** - stateTokens expire quickly (minutes), test in isolation
5. **Use success.href** - Don't construct token redirect URLs manually
6. **Watch for rate limits** - Too many auth attempts triggers 429 responses

## Test Scripts

The `scripts/` directory contains debugging utilities:

| Script                | Purpose                                   |
| --------------------- | ----------------------------------------- |
| `test_timing.py`      | Test introspect timing and cookie flow    |
| `test_identify.py`    | Test through credential submission        |
| `test_mfa_flow.py`    | Full flow test with MFA code argument     |
| `trace_cookies.py`    | Trace cookie flow from HAR file           |
| `compare_requests.py` | Compare browser vs Python request details |
| `analyze_har.py`      | Parse and analyze HAR file structure      |

## References

- Okta IDX API: https://developer.okta.com/docs/api/openapi/idx/idx/tag/Okta-IDX-Authentication-Introspect/
- okta-auth-js: https://github.com/okta/okta-auth-js
- okta-signin-widget: https://github.com/okta/okta-signin-widget
