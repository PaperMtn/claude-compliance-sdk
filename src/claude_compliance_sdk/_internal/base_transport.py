"""HTTP transport abstractions shared by the sync and async clients.

These classes are placeholders during Phase 1. The full sync and async
implementations — request building, header injection, rate limiting,
retry handling, error mapping, and response wrapping — land in Phase 2.
Resource group classes only depend on the interface, not the concrete
implementation, so they will not need to change when Phase 2 fills these
in.
"""


class BaseTransport:
    """Synchronous transport interface. Implementation lands in Phase 2."""


class BaseAsyncTransport:
    """Asynchronous transport interface. Implementation lands in Phase 2."""
