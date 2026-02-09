# paste-stdin

Upload content from stdin to paste.rs and get a shareable URL.

## Usage

```bash
echo "content" | just paste-stdin
cat file.txt | just paste-stdin
```

## Arguments

None - reads from stdin.

## Output

```
https://paste.rs/abc123
```

Returns the URL to view/retrieve the paste.

## Examples

```bash
# Pipe command output
ls -la | just paste-stdin

# Pipe file contents
cat /etc/hosts | just paste-stdin

# Heredoc for multi-line content
cat << 'EOF' | just paste-stdin
SELECT * FROM users;
EOF

# Retrieve on remote server
curl -s https://paste.rs/abc123 -o script.sql
```

## Related Recipes

| Recipe  | Purpose              |
| ------- | -------------------- |
| `paste` | Paste from file path |

## Notes

- paste.rs is a public service; don't upload secrets
- Pastes expire (check paste.rs for retention policy)
- No authentication required
