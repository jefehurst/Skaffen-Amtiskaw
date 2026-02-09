# paste-stdin

Upload stdin to paste.rs.

```bash
echo "content" | just paste-stdin
cat file.txt | just paste-stdin
```

Returns URL: `https://paste.rs/abc123`

Retrieve: `curl -s https://paste.rs/abc123`
