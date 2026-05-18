"""Tests for the ``parse_with_extra`` dataclass-parsing helper."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from claude_compliance_sdk._internal.parsing import parse_with_extra


@dataclass
class _Sample:
    id: str
    name: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def test_known_fields_passed_through_and_extras_captured() -> None:
    parsed = parse_with_extra(_Sample, {"id": "x", "name": "n", "future": 42, "tags": ["a"]})
    assert parsed.id == "x"
    assert parsed.name == "n"
    assert parsed.extra == {"future": 42, "tags": ["a"]}


def test_missing_optional_field_uses_dataclass_default() -> None:
    parsed = parse_with_extra(_Sample, {"id": "only"})
    assert parsed.id == "only"
    assert parsed.name is None
    assert parsed.extra == {}


def test_extra_is_empty_dict_when_no_unknown_keys() -> None:
    parsed = parse_with_extra(_Sample, {"id": "x", "name": "n"})
    assert parsed.extra == {}


def test_extra_key_in_body_does_not_overwrite_extra_dict() -> None:
    # The body can have a key literally named "extra"; it should land
    # in the captured dict alongside other unknowns, not blow away the
    # extra field itself.
    parsed = parse_with_extra(_Sample, {"id": "x", "extra": "weird"})
    assert parsed.extra == {"extra": "weird"}


def test_missing_required_field_raises_type_error() -> None:
    with pytest.raises(TypeError):
        parse_with_extra(_Sample, {"name": "no_id"})


def test_supports_falsy_known_values() -> None:
    # ``None`` and 0 should still be passed through as explicit values
    # rather than dropped as if missing.
    @dataclass
    class WithZero:
        id: str
        count: int = 10
        extra: dict[str, Any] = field(default_factory=dict)

    parsed = parse_with_extra(WithZero, {"id": "x", "count": 0})
    assert parsed.count == 0


def test_works_for_dataclass_with_only_required_fields_and_extra() -> None:
    @dataclass
    class Minimal:
        id: str
        extra: dict[str, Any] = field(default_factory=dict)

    parsed = parse_with_extra(Minimal, {"id": "x", "foo": "bar"})
    assert parsed.id == "x"
    assert parsed.extra == {"foo": "bar"}
