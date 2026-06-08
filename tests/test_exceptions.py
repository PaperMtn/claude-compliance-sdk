"""Unit tests for the exception hierarchy and the response-to-error factory."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from typing import Any

import pytest

from claude_compliance_sdk import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ComplianceClientError,
    ConflictError,
    InsufficientScopeError,
    InternalServerError,
    InvalidAPIKeyError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)
from claude_compliance_sdk.exceptions import _parse_retry_after

# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------


def test_all_errors_descend_from_compliance_client_error() -> None:
    for klass in (
        APIError,
        BadRequestError,
        AuthenticationError,
        InvalidAPIKeyError,
        InsufficientScopeError,
        PermissionDeniedError,
        NotFoundError,
        ConflictError,
        RateLimitError,
        APIStatusError,
        InternalServerError,
        APIConnectionError,
        APITimeoutError,
    ):
        assert issubclass(klass, ComplianceClientError)


def test_http_errors_descend_from_api_error() -> None:
    for klass in (
        BadRequestError,
        AuthenticationError,
        InvalidAPIKeyError,
        InsufficientScopeError,
        PermissionDeniedError,
        NotFoundError,
        ConflictError,
        RateLimitError,
        APIStatusError,
        InternalServerError,
    ):
        assert issubclass(klass, APIError)


def test_invalid_api_key_descends_from_authentication_error() -> None:
    assert issubclass(InvalidAPIKeyError, AuthenticationError)


def test_insufficient_scope_descends_from_permission_denied() -> None:
    # Scope failures are 403, not 401 — see ADR-0003.
    assert issubclass(InsufficientScopeError, PermissionDeniedError)
    assert not issubclass(InsufficientScopeError, AuthenticationError)


def test_timeout_descends_from_connection_error() -> None:
    assert issubclass(APITimeoutError, APIConnectionError)


# ---------------------------------------------------------------------------
# APIError construction
# ---------------------------------------------------------------------------


def test_api_error_carries_all_fields() -> None:
    body = {"error": {"type": "invalid_request_error", "message": "Bad limit."}}
    err = APIError(
        "summary",
        status_code=400,
        request_id="req_abc",
        error_type="invalid_request_error",
        error_message="Bad limit.",
        body=body,
    )
    assert str(err) == "summary"
    assert err.status_code == 400
    assert err.request_id == "req_abc"
    assert err.error_type == "invalid_request_error"
    assert err.error_message == "Bad limit."
    assert err.body is body


# ---------------------------------------------------------------------------
# APIError.from_response — status mapping
# ---------------------------------------------------------------------------


def _spec_body(error_type: str, message: str) -> dict[str, Any]:
    return {"error": {"type": error_type, "message": message}}


@pytest.mark.parametrize(
    "status_code,error_type,message,expected_class",
    [
        (
            400,
            "invalid_request_error",
            "The limit parameter must be between 1 and 1000, inclusive. Got 1500.",
            BadRequestError,
        ),
        (
            403,
            "api_error",
            "Access denied.",
            PermissionDeniedError,
        ),
        (
            404,
            "not_found_error",
            "Chat {id} not found.",
            NotFoundError,
        ),
        (
            409,
            "conflict_error",
            'The "claude_proj_..." project cannot be deleted as it has chats attached to it.',
            ConflictError,
        ),
        (
            500,
            "internal_error",
            "This response would have exceeded the maximum of 1,000 organizations returned.",
            InternalServerError,
        ),
        (502, "internal_error", "bad gateway", InternalServerError),
        (503, "internal_error", "service unavailable", InternalServerError),
        (504, "internal_error", "gateway timeout", InternalServerError),
    ],
)
def test_from_response_routes_status_codes(
    status_code: int,
    error_type: str,
    message: str,
    expected_class: type[APIError],
) -> None:
    err = APIError.from_response(
        status_code=status_code,
        headers={"request-id": "req_xyz"},
        body=_spec_body(error_type, message),
    )
    assert type(err) is expected_class
    assert err.status_code == status_code
    assert err.request_id == "req_xyz"
    assert err.error_type == error_type
    assert err.error_message == message
    assert str(status_code) in str(err)


def test_from_response_unmapped_4xx_uses_api_status_error() -> None:
    err = APIError.from_response(status_code=418, body=_spec_body("teapot_error", "I'm a teapot"))
    assert type(err) is APIStatusError
    assert err.status_code == 418


def test_from_response_unmapped_other_status_falls_back_to_api_error() -> None:
    err = APIError.from_response(status_code=302, body=None)
    assert type(err) is APIError
    assert err.status_code == 302


# ---------------------------------------------------------------------------
# 401 / 403 classification — scope failures are 403 (ADR-0003)
# ---------------------------------------------------------------------------


def test_401_with_invalid_key_message_routes_to_invalid_api_key_error() -> None:
    err = APIError.from_response(
        status_code=401,
        body=_spec_body(
            "authentication_error",
            "The API key provided is invalid or has been revoked.",
        ),
    )
    assert type(err) is InvalidAPIKeyError


def test_401_with_scope_wording_still_routes_to_invalid_api_key_error() -> None:
    # Scope wording in a 401 body must NOT yield InsufficientScopeError;
    # scope failures are 403 (ADR-0003). The only documented 401 is a bad key.
    err = APIError.from_response(
        status_code=401,
        body=_spec_body(
            "authentication_error",
            "The API key provided does not have the `read:compliance_activities` scope.",
        ),
    )
    assert type(err) is InvalidAPIKeyError


@pytest.mark.parametrize(
    "message",
    [
        # All five spec examples from the Error Handling section.
        "The API key provided does not have the `read:compliance_activities` scope "
        "required for this endpoint. Got scopes: [].",
        "The API key provided does not have the `read:compliance_org_data` scope "
        "required for this endpoint. Got scopes: [read:compliance_user_data].",
        "The API key provided does not have the `read:compliance_user_data` scope "
        "required for this endpoint. Got scopes: [].",
        "The API key provided does not have the `delete:compliance_user_data` scope "
        "required for this endpoint. Got scopes: [read:compliance_user_data].",
        "The API key provided does not have the `read:compliance_user_data` scope "
        "required for this endpoint. Got scopes: [read:compliance_activities].",
    ],
)
def test_403_permission_error_routes_to_insufficient_scope_error(message: str) -> None:
    err = APIError.from_response(
        status_code=403,
        body=_spec_body("permission_error", message),
    )
    assert type(err) is InsufficientScopeError


def test_403_with_permission_message_but_other_type_routes_to_insufficient_scope() -> None:
    # Even without the permission_error type, a scope/permission hint in
    # the message refines the 403.
    err = APIError.from_response(
        status_code=403,
        body=_spec_body(
            "forbidden",
            "The API key lacks permission to access this resource.",
        ),
    )
    assert type(err) is InsufficientScopeError


def test_401_with_no_body_falls_back_to_invalid_api_key_error() -> None:
    err = APIError.from_response(status_code=401, body=None)
    assert type(err) is InvalidAPIKeyError
    assert err.error_message is None


# ---------------------------------------------------------------------------
# 429 + Retry-After
# ---------------------------------------------------------------------------


def test_429_parses_retry_after_seconds() -> None:
    err = APIError.from_response(
        status_code=429,
        headers={"Retry-After": "12"},
        body=_spec_body("rate_limit_error", "Rate limit exceeded."),
    )
    assert isinstance(err, RateLimitError)
    assert err.retry_after == 12.0


def test_429_parses_retry_after_http_date() -> None:
    future = datetime.now(tz=timezone.utc) + timedelta(seconds=30)
    err = APIError.from_response(
        status_code=429,
        headers={"retry-after": format_datetime(future, usegmt=True)},
        body=None,
    )
    assert isinstance(err, RateLimitError)
    assert err.retry_after is not None
    assert 20.0 <= err.retry_after <= 30.0


def test_429_without_retry_after_header() -> None:
    err = APIError.from_response(status_code=429, body=None)
    assert isinstance(err, RateLimitError)
    assert err.retry_after is None


def test_429_with_invalid_retry_after_is_none() -> None:
    err = APIError.from_response(
        status_code=429,
        headers={"retry-after": "not a number or date"},
        body=None,
    )
    assert isinstance(err, RateLimitError)
    assert err.retry_after is None


def test_429_past_http_date_clamps_to_zero() -> None:
    past = datetime.now(tz=timezone.utc) - timedelta(seconds=60)
    err = APIError.from_response(
        status_code=429,
        headers={"retry-after": format_datetime(past, usegmt=True)},
        body=None,
    )
    assert isinstance(err, RateLimitError)
    assert err.retry_after == 0.0


# ---------------------------------------------------------------------------
# Header lookup + body parsing edge cases
# ---------------------------------------------------------------------------


def test_request_id_fallback_to_x_request_id() -> None:
    err = APIError.from_response(
        status_code=500,
        headers={"x-request-id": "req_fallback"},
        body=None,
    )
    assert err.request_id == "req_fallback"


def test_non_dict_body_leaves_parsed_fields_unset() -> None:
    err = APIError.from_response(status_code=500, body="oh no")
    assert err.error_type is None
    assert err.error_message is None
    assert err.body == "oh no"


def test_malformed_error_object_leaves_parsed_fields_unset() -> None:
    err = APIError.from_response(status_code=500, body={"error": "not a dict"})
    assert err.error_type is None
    assert err.error_message is None


def test_partial_error_object_parses_what_is_present() -> None:
    err = APIError.from_response(
        status_code=400,
        body={"error": {"message": "boom"}},
    )
    assert err.error_type is None
    assert err.error_message == "boom"


def test_summary_includes_error_type_when_available() -> None:
    err = APIError.from_response(
        status_code=404,
        body=_spec_body("not_found_error", "Chat foo not found."),
    )
    assert "404" in str(err)
    assert "not_found_error" in str(err)
    assert "Chat foo not found." in str(err)


# ---------------------------------------------------------------------------
# _parse_retry_after helper
# ---------------------------------------------------------------------------


def test_parse_retry_after_none_input() -> None:
    assert _parse_retry_after(None) is None


def test_parse_retry_after_empty_input() -> None:
    assert _parse_retry_after("   ") is None


def test_parse_retry_after_fractional_seconds() -> None:
    assert _parse_retry_after("2.5") == 2.5


def test_parse_retry_after_naive_datetime_treated_as_utc() -> None:
    # parsedate_to_datetime returns a naive datetime when no timezone
    # is present in the header; the parser should assume UTC.
    future = datetime.now(tz=timezone.utc) + timedelta(seconds=20)
    naive_no_tz = future.strftime("%a, %d %b %Y %H:%M:%S")  # no GMT/+0000 suffix
    parsed = _parse_retry_after(naive_no_tz)
    assert parsed is not None
    assert 10.0 <= parsed <= 20.0


def test_lookup_header_falls_back_to_title_case_for_plain_dicts() -> None:
    err = APIError.from_response(
        status_code=500,
        headers={"Request-Id": "req_title_case"},
        body=None,
    )
    assert err.request_id == "req_title_case"


# ---------------------------------------------------------------------------
# Top-level re-exports
# ---------------------------------------------------------------------------


def test_top_level_reexports_present() -> None:
    import claude_compliance_sdk as sdk

    for name in (
        "APIConnectionError",
        "APIError",
        "APIStatusError",
        "APITimeoutError",
        "AuthenticationError",
        "BadRequestError",
        "ComplianceClientError",
        "ConflictError",
        "InsufficientScopeError",
        "InternalServerError",
        "InvalidAPIKeyError",
        "NotFoundError",
        "PermissionDeniedError",
        "RateLimitError",
    ):
        assert hasattr(sdk, name), f"missing top-level export: {name}"
        assert name in sdk.__all__, f"missing from __all__: {name}"
