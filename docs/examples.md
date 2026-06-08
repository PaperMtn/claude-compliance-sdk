# Examples

Three runnable scripts shipped under
[`examples/`](https://github.com/PaperMtn/claude-compliance-sdk/tree/main/examples)
in the source tree, drawn from common compliance use cases. Each
reads its API key from `ANTHROPIC_COMPLIANCE_API_KEY` and
takes simple CLI flags — run any of them with `--help` for the
available options.

| Script | Use case | Key type |
| --- | --- | --- |
| [`activity_audit.py`](https://github.com/PaperMtn/claude-compliance-sdk/blob/main/examples/activity_audit.py) | Audit user activity over a time window, optionally filtered by user or activity type. NDJSON output. | Admin (`sk-ant-admin01-...`) |
| [`ediscovery_export.py`](https://github.com/PaperMtn/claude-compliance-sdk/blob/main/examples/ediscovery_export.py) | Export every chat for a set of users in an org, including messages, as JSON files. | Compliance access (`sk-ant-api01-...`) |
| [`file_pull.py`](https://github.com/PaperMtn/claude-compliance-sdk/blob/main/examples/file_pull.py) | Download every user-uploaded file attached to a project. Streamed to disk. | Compliance access (`sk-ant-api01-...`) |

The scripts are intentionally small enough to read in one sitting —
treat them as the canonical examples of how to wire up each resource
group.
