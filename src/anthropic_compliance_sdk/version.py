"""Single source of truth for the SDK version.

The version here must be kept in sync with the ``version`` field in
``pyproject.toml``. The release workflow uses the pyproject value to
tag releases; this constant is what users see at runtime via
``anthropic_compliance_sdk.__version__``.
"""

__version__ = "0.0.0"
