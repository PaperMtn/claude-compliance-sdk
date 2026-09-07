"""Shared pytest fixtures and integration-test helpers."""

from __future__ import annotations

import os

import pytest

from claude_compliance_sdk.client import API_KEY_ENV_VARS

#: Reason string shown when an integration test is skipped.
NO_KEY_REASON = (
    "Requires a live Compliance Access Key in "
    f"{' or '.join(API_KEY_ENV_VARS)} (use sk-ant-api01-...; an Admin "
    "API key reaches the Activity Feed only)."
)


def integration_key() -> str | None:
    """Return a live API key from the environment, if one is set.

    Checks the same variables, in the same order, that the client
    itself resolves. Guarding integration tests on only one of them
    means a correctly configured run silently skips instead.
    """
    for name in API_KEY_ENV_VARS:
        value = os.environ.get(name)
        if value:
            return value
    return None


#: Decorator for tests that need a live API key.
requires_live_key = pytest.mark.skipif(not integration_key(), reason=NO_KEY_REASON)
