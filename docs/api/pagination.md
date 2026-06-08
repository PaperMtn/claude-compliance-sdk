# Pagination

The Compliance API uses two pagination shapes. Cursor pages (Activity
Feed, Chats, Messages) and offset pages (everything else). Both are
modelled here as generic dataclasses, and every paginated resource
ships a `.list()` method returning one page and a `.iter()` method
that auto-paginates.

::: claude_compliance_sdk._internal.pagination
    options:
      members:
        - CursorPage
        - OffsetPage
        - AsyncCursorPage
        - AsyncOffsetPage
