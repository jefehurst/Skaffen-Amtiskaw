ellucian-find: Search Ellucian support portal

USAGE: just ellucian-find "QUERY" [ARGS] PREREQ: just ellucian-login (check: just ellucian-status)

ARGS: QUERY=search terms, ARGS=passthrough to CLI OPTS: --type kb|def, --limit N

EX: just ellucian-find "GUBVERS upgrade" just ellucian-find "session timeout" --type kb

RELATED: ellucian-fetch (get article), ellucian-login, ellucian-status ERR: "Session expired" → just ellucian-login
