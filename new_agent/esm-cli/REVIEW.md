# ESM CLI - Premortem & Code Review

December 2025

______________________________________________________________________

## Premortem: What Could Go Wrong

### 1. Architecture & Scope

| Risk                                        | Impact   | Likelihood | Notes                                                                                 |
| ------------------------------------------- | -------- | ---------- | ------------------------------------------------------------------------------------- |
| Scope creep - trying to automate everything | High     | High       | Focus on upgrade workflow first, then credentials. Full CRUD is Phase 2+              |
| ESM version incompatibility                 | Critical | Medium     | We only have fixtures from ESM 24.2. Field names/structure may differ in 23.x or 25.x |
| No agents/jobs list endpoints               | Medium   | Confirmed  | User stories AGT-1, JOB-1 assumed endpoints that don't exist. Need to revise stories  |

**Recommendation**: Update STORIES.md to reflect reality - remove or defer stories for non-existent endpoints.

### 2. Session Management

| Risk                                  | Impact | Likelihood | Notes                                                      |
| ------------------------------------- | ------ | ---------- | ---------------------------------------------------------- |
| Session expires during long operation | Medium | High       | Current code doesn't detect/handle this                    |
| Missing JSESSIONID on first request   | High   | Confirmed  | Must hit `/admin/` first, not `/admin/login/auth` directly |
| Password change prompt blocks login   | Medium | Low        | `initializeUserPrompt` page needs handling                 |

**Recommendation**: Add session validation wrapper that checks for login redirects before every request.

### 3. Credential Security

| Risk                               | Impact   | Likelihood | Notes                                                    |
| ---------------------------------- | -------- | ---------- | -------------------------------------------------------- |
| Passwords in environment variables | Medium   | Current    | Using `ESM_PASSWORD` env var is acceptable but not ideal |
| Passwords logged in debug output   | Critical | Medium     | No logging implemented yet - must sanitize from day 1    |
| Session cookies stored insecurely  | High     | Medium     | PLAN.md mentions 0600 perms but not implemented          |

**Recommendation**: Implement credential handling before any write operations. Consider keyring integration.

### 4. Error Handling

| Risk                        | Impact | Likelihood | Notes                                                     |
| --------------------------- | ------ | ---------- | --------------------------------------------------------- |
| HTTP 200 with error in body | High   | High       | ESM returns 200 for "Access Denied" - must parse response |
| Silent failures             | High   | Medium     | Current test code doesn't validate response content       |
| Network timeouts            | Medium | Medium     | No timeout configuration                                  |

**Recommendation**: Create response validation layer that checks for error patterns in HTML.

### 5. Testing

| Risk                      | Impact | Likelihood | Notes                                          |
| ------------------------- | ------ | ---------- | ---------------------------------------------- |
| No unit tests             | Medium | Current    | Only ad-hoc test scripts in tmp/               |
| Fixtures may become stale | Medium | High       | ESM upgrades could break parsers               |
| Can't test writes safely  | High   | High       | No test environment; mutations are destructive |

**Recommendation**: Extract HTML from HARs into versioned fixtures. Build parser tests against fixtures.

______________________________________________________________________

## Code Review: Current State

### What Exists

```
esm-cli/
├── fixtures/
│   ├── catalog.md          # Good: Comprehensive endpoint documentation
│   └── har/README.md       # Good: HAR file inventory
├── tmp/                    # Test scripts (not production code)
│   ├── test-readonly.py    # ESMClient prototype
│   └── *.py                # Various debug/test scripts
├── PLAN.md                 # Detailed architecture
├── STORIES.md              # User stories
└── pyproject.toml          # Dependencies only
```

### Code Quality Issues in tmp/test-readonly.py

#### 1. Hardcoded Base URL

```python
BASE = "https://localhost:8999/admin"  # Line 12
```

**Issue**: Not configurable. Should come from config/env. **Fix**: Accept from environment or config file.

#### 2. Import Inside Function

```python
def get_products(self, env_name: str) -> list[dict]:
    import re  # Line 79
```

**Issue**: Import should be at module level. **Fix**: Move to top of file.

#### 3. No Error Handling

```python
def login(self) -> bool:
    self.session.get(f"{BASE}/")  # No try/except
    self.csrf_token = self.session.cookies.get("XSRF-TOKEN")  # Could be None
```

**Issue**: Network errors will crash. Missing CSRF token not handled. **Fix**: Add try/except, validate cookie exists.

#### 4. SSL Verification Disabled Globally

```python
urllib3.disable_warnings()  # Line 10
self.session.verify = False  # Line 18
```

**Issue**: Should be configurable, not always disabled. **Fix**: Accept `--insecure` flag or config option.

#### 5. Magic Strings

```python
if "adminMain" in resp.url:  # Line 36
table = soup.select_one("table.simple-table")  # Multiple places
```

**Issue**: CSS selectors and URL patterns scattered throughout. **Fix**: Centralize in constants or parser config.

#### 6. Inconsistent Return Types

```python
def get_environments(self) -> list[dict]:  # Returns list
def get_environment(self, env_name: str) -> dict:  # Returns dict
```

**Issue**: No data classes, just dicts. Hard to know what fields exist. **Fix**: Use Pydantic models or dataclasses.

#### 7. No Retry Logic

```python
resp = self.session.post(...)  # Single attempt
```

**Issue**: Transient failures will crash. **Fix**: Add retry with backoff for network errors.

### What's Missing

1. **No src/ directory** - All code is in tmp/
2. **No CLI entry point** - No Click commands yet
3. **No tests** - Only manual test scripts
4. **No configuration** - Hardcoded values everywhere
5. **No session persistence** - Cookies not saved to disk
6. **No logging** - Only print statements
7. **No type checking** - mypy not configured

______________________________________________________________________

## Recommended Next Steps

### Immediate (Before More Features)

1. **Create proper project structure** ✅ DONE

   ```
   src/esm/
   ├── __init__.py
   ├── client.py      # ESMClient with error handling
   ├── config.py      # Configuration from env vars
   ├── exceptions.py  # Custom exceptions
   ├── selectors.py   # Centralized CSS selectors and URL patterns
   └── parsers/
       ├── __init__.py
       └── base.py    # Table parsing utilities
   ```

2. **Add error handling wrapper** ✅ DONE

   - `_check_response()` validates all responses
   - Detects session expiry, access denied, password change prompts
   - Custom exceptions: `SessionExpiredError`, `PermissionDeniedError`, etc.

3. **Extract fixtures for testing** ✅ DONE

   - Copied 8 HTML fixtures to `tests/fixtures/v24/`
   - Created pytest fixtures in `conftest.py`
   - 11 parser tests passing

4. **Update STORIES.md** ✅ DONE

   - Marked AGT-1, AGT-2, AGT-3, AGT-4 as DEFERRED (no endpoint)
   - Marked JOB-1 as DEFERRED (requires installId from job start)
   - Updated implementation order

5. **Centralize magic strings** ✅ DONE

   - All CSS selectors in `selectors.py` with `get_selectors(version)`
   - All URL patterns in `URL_PATTERNS` dict
   - Version-specific overrides supported

### Before Write Operations

1. **Session persistence** - Save/load cookies
2. **Credential security** - Don't log passwords
3. **Idempotency checking** - Read before write
4. **Dry-run mode** - `--check` flag

### Before Ansible Integration

1. **JSON output mode** - `--json` flag
2. **Proper exit codes** - 0/1/2 for success/failure/error
3. **Changed detection** - Report if mutation occurred

______________________________________________________________________

## Summary

**Good**:

- Comprehensive planning documentation
- HAR captures cover core workflow
- Live API testing validates approach
- Core parsing logic works
- ✅ Production code structure in `src/esm/`
- ✅ Error handling and response validation
- ✅ Centralized selectors with version support
- ✅ Unit tests with HTML fixtures
- ✅ Configuration from environment variables

**Needs Work**:

- ~~No production code structure yet~~ ✅ Done
- ~~Error handling missing~~ ✅ Done
- ~~No tests~~ ✅ Done
- ~~Configuration hardcoded~~ ✅ Done
- ~~Some user stories based on non-existent endpoints~~ ✅ Done
- No CLI entry point yet (Click commands)
- No session persistence
- No logging framework

**Risk Level**: Low for read operations - Good foundation with proper structure and error handling. Write operations
still need additional safeguards.
