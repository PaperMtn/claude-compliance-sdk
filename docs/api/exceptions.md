# Errors

Every error raised by the SDK descends from `ComplianceClientError`.
HTTP failures live under `APIError` (with a typed subclass per
status code); transport-level failures live under `APIConnectionError`.

::: claude_compliance_sdk.exceptions
    options:
      members:
        - ComplianceClientError
        - APIError
        - BadRequestError
        - AuthenticationError
        - InvalidAPIKeyError
        - InsufficientScopeError
        - PermissionDeniedError
        - NotFoundError
        - ConflictError
        - RateLimitError
        - APIStatusError
        - InternalServerError
        - APIConnectionError
        - APITimeoutError
        - FileTooLargeError
