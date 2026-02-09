# ellucian-login

Authenticate to Ellucian support portal. Required before using search/fetch.

## Usage

```bash
# Interactive login (prompts for MFA)
just ellucian-login

# Login with MFA code directly
just ellucian-login-mfa CODE
```

## Authentication Flow

1. Run `just ellucian-login`
2. Browser opens for SSO
3. Complete MFA prompt
4. Session stored in `~/.cache/ellucian-support/`

## Session Duration

Sessions typically last ~2 hours. Use keepalive to extend:

```bash
# Check if still valid
just ellucian-status

# Keep session alive (single ping)
just ellucian-keepalive

# Background keepalive loop
just ellucian-keepalive-loop
```

## Related Recipes

| Recipe                    | Purpose                      |
| ------------------------- | ---------------------------- |
| `ellucian-status`         | Check current session        |
| `ellucian-keepalive`      | Single session refresh       |
| `ellucian-keepalive-loop` | Background refresh every 90s |
| `ellucian-login-mfa`      | Login with MFA code          |

## Troubleshooting

**MFA timeout**: Run again. MFA codes expire quickly.

**Browser doesn't open**: Check DISPLAY env var or use `ellucian-login-mfa`.

**"Invalid credentials"**: Verify account has support portal access.

## Environment

Requires `local.env` with credentials. See `profiles/ellucian.md`.
