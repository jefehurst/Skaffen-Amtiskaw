# ellucian-status

Check if Ellucian support session is valid.

## Usage

```bash
just ellucian-status
```

## Output

- Success: Session info and expiration
- Failure: "Session expired" or "Not logged in"

## Related Recipes

- `ellucian-login` - Authenticate if expired
- `ellucian-keepalive` - Refresh session
- `ellucian-keepalive-loop` - Background refresh

## Use Before

Always check status before search/fetch operations to avoid errors.
