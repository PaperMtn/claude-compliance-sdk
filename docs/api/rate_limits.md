# Rate limits

The Compliance API allows 600 requests per minute per **parent
organisation** — one budget shared across every key beneath it and
every `/v1/compliance/*` endpoint. The remote session endpoints carry a
second budget on top of that.

The SDK reads the server's `anthropic-ratelimit-*` response headers and
waits for the stated reset when the budget is spent, rather than
spending a request to discover a 429. Read the latest observation from
`client.rate_limit_status` to pace your own workers.

```python
page = client.activities.list(limit=100)
status = client.rate_limit_status
if status and status.remaining is not None and status.remaining < 50:
    ...  # Slow down: the budget is shared with every other consumer.
```

`rate_limit_rpm` on the client caps how fast *this* client will issue
requests. Setting it to `0` disables that local window, but the
server-reported budget is still honoured.

::: claude_compliance_sdk._internal.rate_limit
    options:
      members:
        - RateLimitSnapshot
