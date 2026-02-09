# Profile: Banner Troubleshooting

Load this profile when working on Banner/Oracle database issues, upgrade problems, or general Ellucian Banner
troubleshooting.

## Information Lookup Priority

1. **Confluence Knowledge Base** - Previously internalized vendor articles (`mcp__atlassian__confluence_search`)
2. **Logseq journals** - Past troubleshooting sessions, notes
3. **Ellucian Support** - Knowledge base, defects (requires MFA - ask first!)
4. **Web search** - Last resort, usually unhelpful for vendor products

**After finding useful vendor documentation**: Publish to Confluence Knowledge Base (see Behavioral Corrections section)

## Key Oracle Tables

### Version Tracking

| Table   | Purpose                          | Key Columns                                     |
| ------- | -------------------------------- | ----------------------------------------------- |
| GUBVERS | Banner baseline versions         | GUBVERS_OBJECT_NAME, GUBVERS_RELEASE            |
| GURWADB | Web/Admin application deployment | GURWADB_APPLICATION_NAME, GURWADB_ACTIVITY_DATE |

Always use `DESC <table>` to verify column names - documentation often differs from reality.

### BYPASS Method for Re-applying Upgrades

When ESM marks a failed upgrade as complete, use BYPASS to allow restart:

```sql
-- Mark as BYPASS to allow re-selection in ESM
UPDATE GURWADB
SET GURWADB_RELEASE = '9.40.2_BYPASS'
WHERE GURWADB_APPLICATION_NAME = 'BannerDbUpgrade'
  AND GURWADB_RELEASE = '9.40.2';
COMMIT;

-- After successful completion, reset to normal
UPDATE GURWADB
SET GURWADB_RELEASE = '9.40.2'
WHERE GURWADB_APPLICATION_NAME = 'BannerDbUpgrade'
  AND GURWADB_RELEASE = '9.40.2_BYPASS';
COMMIT;
```

Reference: Ellucian Articles 000046496, 000511193

### Common Queries

```sql
-- Check Banner baseline version
SELECT * FROM GUBVERS WHERE GUBVERS_OBJECT_NAME = 'BANNER';

-- Check deployed applications
SELECT GURWADB_APPLICATION_NAME, GURWADB_ACTIVITY_DATE
FROM GURWADB
ORDER BY GURWADB_ACTIVITY_DATE DESC;

-- Check object validity
SELECT object_name, object_type, status
FROM dba_objects
WHERE status = 'INVALID'
AND owner = 'BANINST1';

-- Check active sessions
SELECT sid, serial#, username, status,
       sql_id, event, seconds_in_wait,
       module, action
FROM v$session
WHERE username IS NOT NULL
  AND username NOT IN ('SYS', 'SYSTEM')
ORDER BY seconds_in_wait DESC;

-- Kill all user sessions (generates statements)
SELECT 'ALTER SYSTEM KILL SESSION ''' || sid || ',' || serial# || ''' IMMEDIATE;'
FROM v$session
WHERE type = 'USER'
  AND username IS NOT NULL
  AND username NOT IN ('SYS', 'SYSTEM')
  AND sid != (SELECT sid FROM v$mystat WHERE rownum = 1);

-- Check blocking locks
SELECT
    blocker.sid AS blocker_sid,
    blocker.serial# AS blocker_serial,
    blocker.username AS blocker_user,
    waiter.sid AS waiting_sid,
    waiter.username AS waiting_user,
    waiter.seconds_in_wait
FROM v$session waiter
JOIN v$session blocker ON waiter.blocking_session = blocker.sid
WHERE waiter.blocking_session IS NOT NULL
ORDER BY waiter.seconds_in_wait DESC;

-- Check database restricted mode
SELECT logins FROM v$instance;
-- RESTRICTED = restricted mode on, ALLOWED = normal mode
```

## Common File Locations

### Upgrade Files

| Path Pattern                                      | Contents                   |
| ------------------------------------------------- | -------------------------- |
| `/u01/sct/<ENV>/upgrades/<upgrade-name>/`         | Upgrade package root       |
| `/u01/sct/<ENV>/upgrades/<upgrade-name>/spfiles/` | SQL spool/log files (.lst) |
| `/u01/sct/<ENV>/upgrades/<upgrade-name>/logs/`    | Installer logs             |

### Application Logs

| Path Pattern                 | Contents              |
| ---------------------------- | --------------------- |
| `/u01/sct/<ENV>/admin/logs/` | Admin app logs        |
| `/u01/sct/<ENV>/ssb/logs/`   | Self-service logs     |
| `$BANNER_HOME/general/exe/`  | Compiled Banner forms |

**Always provide absolute paths** when referencing files the user should check.

## Sharing Files from Remote Servers

When you need me to review a large file (groovy configs, logs, etc.) that's impractical to paste:

```bash
curl -sF 'f:1=<-' ix.io < filename
```

**Fallbacks** (if ix.io is down or blocked):

```bash
curl -sF 'file=@-' 0x0.st < filename
nc termbin.com 9999 < filename
```

This returns a URL I can fetch with WebFetch. Offer this option when:

- Groovy configuration files need review
- Log files or diffs are too large to paste
- Multiple files need comparison
- Any situation where "paste me the file" would be awkward

Works with pipes too: `diff -u old.groovy new.groovy | curl -sF 'f:1=<-' ix.io`

**Note**: Enterprise servers may have outbound restrictions. If all pastebins fail, fall back to targeted greps or
asking user to paste relevant sections.

## Shell Command Conventions

### SQL File Creation

Use heredoc syntax for multi-line SQL:

```bash
cat << 'EOF' > fix_script.sql
-- Description of what this fixes
WHENEVER SQLERROR EXIT SQL.SQLCODE
SET ECHO ON

-- SQL statements here

EXIT;
EOF
```

### Running SQL Scripts

```bash
sqlplus username/password@SID @script.sql | tee script.log
```

### Database Change Logging (REQUIRED)

When making changes to ANY database (production or otherwise):

1. **Log BEFORE execution** to SESSION_LOG.md:

   ```markdown
   ## Database Change - [timestamp]
   **Database**: [PROD/DEVL/etc] PDB: [pdb_name]
   **SQL**: [the statement]
   **Purpose**: [why]
   ```

2. **Log AFTER execution**:

   ```markdown
   **Result**: [rows affected, errors, or success]
   ```

3. **For destructive operations**, document rollback plan FIRST

This creates an audit trail. The user explicitly instructed: "We're making changes to the PROD DB, you should be logging
them."

### Pluggable Database Context (REQUIRED)

When providing Oracle commands for multi-tenant environments:

1. **ALWAYS specify which PDB/container** the command targets
2. Include container context:
   ```sql
   ALTER SESSION SET CONTAINER = PROD;  -- Or the appropriate PDB name
   ```
3. **Never assume** the user knows which container they should be in

The user instructed: "PROD is a PDB. Please indicate which container we should be in."

**Common pattern**:

```sql
-- First, show current container and available PDBs
SHOW CON_NAME;
SELECT name, open_mode FROM v$pdbs;

-- Then switch to target
ALTER SESSION SET CONTAINER = PROD;
```

## Ellucian Support Workflow

The `ellucian-support` CLI requires Okta MFA. Sessions expire frequently.

**Before searching**:

1. Ask user for MFA code
2. Login: `echo "<code>" | poetry run ellucian-support login -f`
3. Then search: `poetry run ellucian-support find "query" --source kb`

**Search sources**:

- `--source kb` - Knowledge base (troubleshooting)
- `--source docs` - Official documentation
- `--source defect` - Known bugs

## Documentation Output

When documenting findings:

- Store in `docs/ellucian/` with descriptive names
- Update `docs/INDEX.md` if creating new topic areas
- Include actual schema output, not guessed column names
- Note discrepancies between docs and reality

## Common Issues Checklist

When troubleshooting Banner issues:

- [ ] Check object validity (`dba_objects WHERE status = 'INVALID'`)
- [ ] Review recent upgrade logs in `spfiles/`
- [ ] Verify version in GUBVERS matches expected
- [ ] Check for locked accounts or expired passwords
- [ ] Review listener status (`lsnrctl status`)
- [ ] Check alert log for ORA- errors

## Tomcat/JVM Timezone Configuration

Banner web applications (ESM, ODS Admin UI, SSB, etc.) use the JVM timezone. By default this may be UTC instead of local
time, causing:

- Wrong times displayed in web interfaces
- Scheduled jobs running at unexpected times
- Timestamp mismatches between UI and log files

### Fix: Set JVM Timezone

Add `-Duser.timezone` to Tomcat's `setenv.sh`:

```bash
# Location: /u01/apache-tomcat-*/bin/setenv.sh
# Create if it doesn't exist

JAVA_OPTS="$JAVA_OPTS -Duser.timezone=America/Los_Angeles"
```

**Use IANA timezone names** (e.g., `America/Los_Angeles`, `America/New_York`), not abbreviations like `PST`.

After restart, verify with:

```bash
ps -ef | grep java | grep timezone
# Should show: -Duser.timezone=America/Los_Angeles
```

**References**:

- **Ellucian Article 000502999** - ESM Interface using UTC instead of local time
- **Ellucian Article 000047974** - Banner ESS incorrectly calculating dates with certain timezones

### Ellucian Article 000502999 - ESM UTC Time Issue (Verbatim)

> **Issue**: If your ESM interface is using UTC time for the dates and times of Upgrades and Deployments, and you want
> it to show local time, so it matches the dates and times in the `$BANNER_HOME/bmui/logs` directory.
>
> **Solution**: Add `-Duser.timezone=America/New_York` to the `setenv.sh` and restart ESM. (Replace "America/New_York"
> with your local time zone)
>
> If the `setenv.sh` doesn't exist in your tomcat bin directory (`/u01/apache-tomcat-8.5.30/bin`, for example), you can
> create one with the line:
>
> ```
> JAVA_OPTS="$JAVA_OPTS -Duser.timezone=America/New_York"
> ```
>
> This will not correct any upgrades that have already been recorded with UTC time, but it will ensure that local time
> is used going forward.

### Ellucian Article 000047974 - Timezone Calculation Issues (Summary)

Certain timezones (notably `Asia/Baku`) can cause date calculation errors in Banner Self-Service due to DST handling
bugs in older Linux versions (BUG 1318979).

**Workaround** (only for non-DST timezones with issues):

```bash
export JAVA_OPTS="$JAVA_OPTS -Duser.timezone=UTC+4"
```

**Warning**: Using `UTC+/-X` format breaks DST transitions. Only use named timezones (`America/New_York`) if you observe
DST.

**Note**: Setting `-Duser.timezone=UTC` may cause date errors in BannerAdmin FTVORGN.

## ESM Timeout Issues

ESM has configurable timeouts that may abort long-running scripts:

- Default appears to be 600 seconds (10 min) for some operations
- 3600 seconds (1 hour) for others
- Setting: "Banner Wait For (secs)" in ESM configuration (Ellucian Article 000037444)

**When ESM times out but script is still running**:

1. Check if Oracle session still exists (query v$session)
2. Let it complete
3. Restart ESM - it should recognize completion and continue

**When ESM times out and kills the session**:

1. Run the script manually to completion
2. Restart ESM

**Stubbing out completed scripts**:

If a script completed manually but ESM keeps re-running it:

```bash
cp script.sql script.sql.bak
cat << 'EOF' > script.sql
-- Already applied manually YYYY-MM-DD
-- Original backed up to script.sql.bak
BEGIN
  NULL;
END;
/
EOF
```

## OCI Base Database Service - PDB Service Management

On OCI Base Database Service, PDB services are managed via `srvctl`, not `DBMS_SERVICE`.

### Starting a PDB Service

```bash
srvctl start service -db ${ORACLE_UNQNAME} -service <service_name>
```

Example:

```bash
srvctl start service -db bannprdb -service DEVL.example.edu
```

### Checking Service Status

```bash
srvctl status service -db ${ORACLE_UNQNAME}
lsnrctl status | grep -i "<service_name>"
```

### Why This Matters

When a PDB is opened (even after restricted mode), its services may not automatically register with the listener. Using
`srvctl start service` properly registers the service and ensures it persists across restarts.

## Application Configuration Types

Not all Banner 9 apps use groovy configs:

| Application                              | Framework       | Config Type              |
| ---------------------------------------- | --------------- | ------------------------ |
| AppNav, SSB apps                         | Grails          | `*_configuration.groovy` |
| BannerAdmin, AdminCommon, AdminCommon.ws | Morphis toolkit | `.properties` files      |
| Banner Access Manager (BAM)              | Morphis toolkit | `.properties` files      |

When troubleshooting auth issues, check the right config type for the affected application.

## Behavioral Corrections

This section collects corrections and refinements from actual troubleshooting sessions. Update immediately when the user
provides corrections or useful insights.

**Correction Types**:

- **Behavioral**: How I approached something wrong → add here
- **Factual**: Wrong file path, table name, etc. → update the relevant section directly

### 2025-12-14 - Get Ticket Number First

**Problem**: Started troubleshooting without recording the ticket number, had to ask later **Correction**: At the start
of any new troubleshooting effort, ask for the ticket number and add it to STATUS.md immediately

### 2025-12-08 - Search Priority

**Problem**: Searched web or made assumptions before checking Ellucian support **Correction**: Always search Ellucian
support first for Banner/ESM issues - ask for MFA code upfront

### 2025-12-08 - Column Name Guessing

**Problem**: Guessed column name as `GURWADB_INSTALL_DATE` instead of checking **Correction**: Use `DESC <table>` to get
exact column names before documenting or querying

### 2025-12-08 - File Path Specificity

**Problem**: Gave filename without full path for spool file **Correction**: Always provide absolute paths when
referencing files user should check

### 2025-12-29 - ODS Timezone Uses CDB, Not PDB

**Problem**: Spent significant time checking PDB timezone settings for ODS UTC display issue. All PDB settings were
correct but ODS still showed UTC.

**Correction**: ODS/OWBSYS uses the **CDB DBTIMEZONE**, not the PDB timezone. In multitenant environments, always check
CDB$ROOT timezone first for ODS issues.

**Gotcha**: If the database auto-switches to PDB on login, `SELECT DBTIMEZONE FROM DUAL` will show PDB value, masking
the CDB setting. Explicitly `ALTER SESSION SET CONTAINER = CDB$ROOT` before checking.

### 2025-12-08 - Internalize Vendor Documentation

**Problem**: Fetched articles but only summarized findings in conversation **Correction**: When fetching documentation
from **vendor sources** (Ellucian, Oracle, Runner, etc.), publish to Confluence Knowledge Base space. This prevents
re-fetching the same information in future sessions.

**Where to publish**:

- **Confluence Knowledge Base space** (via Atlassian MCP) - preferred destination for vendor documentation
- Use `mcp__atlassian__confluence_search` to check if article already exists
- Use `mcp__atlassian__confluence_create_page` to publish new articles

**Article format**:

```markdown
# [Article Number] - [Title]

> **Source**: [Vendor] Support - [Article URL or ID]
> **Retrieved**: [Date]
> **Applies to**: [Product/Version]

[Article content in markdown - verbatim for short articles, summarized for long ones]
```

**For AI-generated content** (analysis, summaries, procedures I write):

```markdown
> ⚠️ **AI-Generated Content**: This document was created by Claude. Review for accuracy before relying on it.
```

**Does NOT apply to**: Stack Overflow, blog posts, forum discussions, or other community content. Those are ephemeral
references, not authoritative documentation worth preserving.

______________________________________________________________________

## Consolidation Log

Review after ~10 corrections. Promote patterns to main sections, archive one-offs.

<!-- Format:
### [Date] - Consolidation
- Promoted: [correction] → [section]
- Archived: [correction] (reason)
-->

*No consolidations yet.*
