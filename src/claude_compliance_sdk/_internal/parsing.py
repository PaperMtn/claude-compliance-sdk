"""Helpers for parsing Compliance API response bodies into dataclasses.

Every typed response in the SDK (``Activity``, ``Chat``, ``Project``,
``Organization``, ``Role``, …) follows the same recipe: a handful of
known top-level fields modelled as dataclass attributes, plus an
``extra: dict[str, Any]`` field that captures activity-type-specific
keys and any new top-level fields the spec adds later. The split
between known and unknown keys is a *property of the dataclass* — it
should be derived from the field set, not maintained by hand in a
parallel frozenset.

:func:`parse_with_extra` walks ``dataclasses.fields(cls)`` to discover
the known names, copies matching body values to constructor kwargs, and
dumps everything else into ``extra``. Resource dataclasses keep a
one-line ``from_dict`` that delegates to this helper.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping, TypeVar

T = TypeVar("T")


def parse_with_extra(cls: type[T], body: Mapping[str, Any]) -> T:
    """Build a dataclass from a response body, capturing unknowns in ``extra``.

    The dataclass must define an ``extra: dict[str, Any]`` field with a
    default factory; every body key not matching another known field is
    copied into it verbatim. Body keys that *are* known are passed
    through to the constructor; missing optional fields fall back to
    the dataclass's default, missing required fields raise the usual
    :class:`TypeError` from the dataclass ``__init__``.

    Args:
        cls: The dataclass type to instantiate.
        body: Decoded JSON body for one record.

    Returns:
        An instance of ``cls`` with known fields populated and
        ``extra`` carrying any leftover keys.
    """
    # dataclasses.fields expects a DataclassInstance protocol from _typeshed,
    # not generic TypeVars. Callers pass dataclass types in practice; the
    # ignore keeps the public signature ergonomic.
    fields = dataclasses.fields(cls)  # type: ignore[arg-type]
    known_names = {f.name for f in fields if f.name != "extra"}
    kwargs: dict[str, Any] = {name: body[name] for name in known_names if name in body}
    kwargs["extra"] = {k: v for k, v in body.items() if k not in known_names}
    return cls(**kwargs)
