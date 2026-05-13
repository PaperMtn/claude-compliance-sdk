"""Smoke tests for the public construction surface of both clients.

These tests assert the things that are stable across phases: the
resource group attributes exist, configuration arguments are honoured,
the API key falls back to the environment variable, and missing keys
fail loudly. Behavioural tests for the resource methods themselves
arrive in Phase 3.
"""

import pytest

from anthropic_compliance_sdk import AsyncComplianceClient, ComplianceClient, __version__
from anthropic_compliance_sdk.client import API_KEY_ENV_VAR

RESOURCE_GROUPS = (
    "activities",
    "artifacts",
    "chats",
    "files",
    "generated_files",
    "groups",
    "organizations",
    "project_documents",
    "projects",
    "roles",
)


@pytest.fixture
def fake_api_key() -> str:
    return "sk-ant-api01-test-key"


def test_version_is_a_string() -> None:
    assert isinstance(__version__, str)
    assert __version__


@pytest.mark.parametrize("client_cls", [ComplianceClient, AsyncComplianceClient])
def test_constructor_accepts_explicit_api_key(client_cls: type, fake_api_key: str) -> None:
    client = client_cls(api_key=fake_api_key)
    assert client._api_key == fake_api_key  # noqa: SLF001 — testing internal state


@pytest.mark.parametrize("client_cls", [ComplianceClient, AsyncComplianceClient])
def test_constructor_falls_back_to_env_var(
    client_cls: type, fake_api_key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(API_KEY_ENV_VAR, fake_api_key)
    client = client_cls()
    assert client._api_key == fake_api_key  # noqa: SLF001


@pytest.mark.parametrize("client_cls", [ComplianceClient, AsyncComplianceClient])
def test_constructor_raises_when_no_api_key_anywhere(
    client_cls: type, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    with pytest.raises(ValueError, match="No API key provided"):
        client_cls()


@pytest.mark.parametrize("client_cls", [ComplianceClient, AsyncComplianceClient])
@pytest.mark.parametrize("group_name", RESOURCE_GROUPS)
def test_resource_groups_are_present(client_cls: type, group_name: str, fake_api_key: str) -> None:
    client = client_cls(api_key=fake_api_key)
    assert hasattr(client, group_name)
    assert getattr(client, group_name) is not None


@pytest.mark.parametrize("client_cls", [ComplianceClient, AsyncComplianceClient])
def test_constructor_overrides_defaults(client_cls: type, fake_api_key: str) -> None:
    client = client_cls(
        api_key=fake_api_key,
        base_url="https://example.test",
        timeout=5.0,
        anthropic_version="2099-01-01",
        max_download_bytes=1024,
        max_retries=7,
        rate_limit_rpm=300,
    )
    assert client.base_url == "https://example.test"
    assert client.timeout == 5.0
    assert client.anthropic_version == "2099-01-01"
    assert client.max_download_bytes == 1024
    assert client.max_retries == 7
    assert client.rate_limit_rpm == 300


def test_sync_client_supports_context_manager(fake_api_key: str) -> None:
    with ComplianceClient(api_key=fake_api_key) as client:
        assert isinstance(client, ComplianceClient)


@pytest.mark.asyncio
async def test_async_client_supports_context_manager(fake_api_key: str) -> None:
    async with AsyncComplianceClient(api_key=fake_api_key) as client:
        assert isinstance(client, AsyncComplianceClient)
