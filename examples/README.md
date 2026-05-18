# Examples

Runnable end-to-end scripts using `claude-compliance-sdk`. Each
script reads its API key from `ANTHROPIC_COMPLIANCE_API_KEY` and
takes simple CLI args.

| Script | Use case | Key type |
| --- | --- | --- |
| [`activity_audit.py`](activity_audit.py) | Audit user activity over a time window, optionally filtered by user or activity type. NDJSON output. | Admin (`sk-ant-admin01-...`) |
| [`ediscovery_export.py`](ediscovery_export.py) | Export every chat for a set of users in an org, including messages, as JSON files. | Compliance access (`sk-ant-api01-...`) |
| [`file_pull.py`](file_pull.py) | Download every user-uploaded file attached to a project. Streamed to disk. | Compliance access (`sk-ant-api01-...`) |

Run any of them with `--help` for the available flags.
