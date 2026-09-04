# Examples

Runnable end-to-end scripts using `claude-compliance-sdk`. Each
script reads its API key from `ANTHROPIC_COMPLIANCE_ACCESS_KEY` and
takes simple CLI args.

| Script | Use case | Key type |
| --- | --- | --- |
| [`activity_audit.py`](activity_audit.py) | Audit user activity over a time window, optionally filtered by user or activity type. NDJSON output. | Either (`sk-ant-api01-...` or `sk-ant-admin01-...`) |
| [`ediscovery_export.py`](ediscovery_export.py) | Export chats org-wide (or for named users with --user), including messages, as JSON files. | Compliance access (`sk-ant-api01-...`) |
| [`file_pull.py`](file_pull.py) | Download every user-uploaded file attached to a project. Streamed to disk. | Compliance access (`sk-ant-api01-...`) |
| [`session_export.py`](session_export.py) | Export Cowork / Claude Code / Claude Science session transcripts over a time window, one JSON file per session. | Compliance access (`sk-ant-api01-...`) |

Run any of them with `--help` for the available flags.
