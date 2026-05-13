"""Transport interface shared by the sync and async clients.

Resource group classes type-hint their transport against these
abstract bases so they can be instantiated with the real
:class:`~claude_compliance_sdk._internal.transport.SyncTransport` /
:class:`~claude_compliance_sdk._internal.transport.AsyncTransport`
implementations from Phase 2.2 onward, or with a test double that
provides the same surface.

The concrete classes live in
:mod:`claude_compliance_sdk._internal.transport`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping


class BaseTransport(ABC):
    """Synchronous transport interface."""

    @abstractmethod
    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        stream: bool = False,
    ) -> Any:
        """Send a request and return the decoded body."""

    @abstractmethod
    def close(self) -> None:
        """Release any underlying HTTP resources."""


class BaseAsyncTransport(ABC):
    """Asynchronous transport interface."""

    @abstractmethod
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        stream: bool = False,
    ) -> Any:
        """Send a request and return the decoded body."""

    @abstractmethod
    async def aclose(self) -> None:
        """Release any underlying HTTP resources."""
