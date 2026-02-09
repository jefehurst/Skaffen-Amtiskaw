# just sessions-mark

Mark a session as reviewed in the reflection tracking system.

## Usage

```bash
just sessions-mark SESSION_ID [FINDINGS]
```

## Arguments

| Argument   | Required | Default | Description                                     |
| ---------- | -------- | ------- | ----------------------------------------------- |
| SESSION_ID | Yes      | -       | UUID of the session to mark                     |
| FINDINGS   | No       | 0       | Number of actionable findings from this session |

## Examples

```bash
# Mark session with no findings
just sessions-mark 00d8ee78-e164-400f-ba29-3155a2e46313

# Mark session with 3 findings
just sessions-mark 23ddab2e-897c-4a0c-b260-e766021cd0fc 3
```

## Output

```
Marked 23ddab2e-897c-4a0c-b260-e766021cd0fc as reviewed
```

## How It Works

Updates `reflect/reviewed.tsv` with:

- Session ID
- Current modification time of the session file
- Today's date as review date
- Findings count

If the session was previously marked, updates the existing entry.

## Related

- `just sessions-pending` - See which sessions need review
- `just sessions-summary` - Quick counts
- `just analyze-sessions` - Find patterns in sessions
