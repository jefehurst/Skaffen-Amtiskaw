ellucian-login: Authenticate to Ellucian support portal

USAGE: just ellucian-login (interactive) just ellucian-login-mfa CODE (with MFA)

FLOW: run → browser SSO → MFA → session stored SESSION: ~2hr duration, stored in ~/.cache/ellucian-support/

KEEPALIVE: just ellucian-status (check) just ellucian-keepalive (ping) just ellucian-keepalive-loop (background)

RELATED: ellucian-status, ellucian-find, ellucian-fetch PREREQ: local.env with credentials (see profiles/ellucian.md)
ERR: MFA timeout → retry; no browser → use ellucian-login-mfa
