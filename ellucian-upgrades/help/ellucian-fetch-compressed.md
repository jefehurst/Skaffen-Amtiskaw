ellucian-fetch: Get full Ellucian article content

USAGE: just ellucian-fetch ARTICLE PREREQ: just ellucian-login (check: just ellucian-status)

ARTICLE: article number (000502999), full URL, or sys_id OUTPUT: markdown with title, body, attachments

EX: just ellucian-fetch 000502999 just ellucian-fetch "https://ellucian.service-now.com/..."

WORKFLOW: ellucian-find → ellucian-fetch → publish to ITKB RELATED: ellucian-find, ellucian-login, ellucian-status ERR:
"not found" → verify ID; "expired" → just ellucian-login
