# paste

Upload a file to paste.rs and get a shareable URL.

## Usage

```bash
just paste FILE
```

## Arguments

| Arg  | Description            |
| ---- | ---------------------- |
| FILE | Path to file to upload |

## Output

```
https://paste.rs/abc123
curl -sk https://paste.rs/abc123
```

Returns:

1. URL to view/share the paste
2. curl command to retrieve content

## Examples

```bash
# Upload a log file
just paste /tmp/debug.log

# Upload script output
some-command > /tmp/output.txt && just paste /tmp/output.txt

# Upload from stdin (different recipe)
echo "content" | just paste-stdin
```

## Related Recipes

| Recipe        | Purpose          |
| ------------- | ---------------- |
| `paste-stdin` | Paste from stdin |

## Notes

- paste.rs is a public service; don't upload secrets
- Pastes expire (check paste.rs for retention policy)
- No authentication required
