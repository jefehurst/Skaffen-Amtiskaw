# just sessions-summary

Show session review statistics.

## Usage

```bash
just sessions-summary
```

## Output

```
Sessions: 346 total, 6 reviewed, 234 pending
```

| Metric   | Description                                                  |
| -------- | ------------------------------------------------------------ |
| total    | All session files in the project's Claude sessions directory |
| reviewed | Sessions recorded in `reflect/reviewed.tsv`                  |
| pending  | Sessions that are new or modified since last review          |

## Related

- `just sessions-pending` - List the pending sessions
- `just sessions-mark ID [N]` - Mark a session as reviewed
