# claude-compliance-sdk

A community Python SDK for the Anthropic Compliance API.

> **Status:** in development. Not yet published to PyPI.
>
> **Unofficial:** this is a community-maintained project. It is not produced,
> endorsed, or supported by Anthropic.

A hand-written, dependency-light SDK with sync and async parity, modelled on
the ergonomics of `slack_sdk`. Supports the Activity Feed, Chats, Files,
Projects, Organizations, Roles, and Groups endpoints of the Anthropic
Compliance API.

```python
from claude_compliance_sdk import ComplianceClient

with ComplianceClient(api_key="sk-ant-api01-...") as client:
    ...  # resource methods land in a later phase
```

Full quickstart, usage examples, and API reference will land in a later phase.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
