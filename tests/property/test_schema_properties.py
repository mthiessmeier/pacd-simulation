"""Bounded properties for strict, immutable configuration schemas."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from pacd_sim.schema import StrictFrozenModel


class _SchemaProbe(StrictFrozenModel):
    identifier: str
    enabled: bool
    count: int


_EXTRA_NAMES = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz_",
    min_size=1,
    max_size=20,
).filter(lambda value: value not in {"identifier", "enabled", "count"})
_JSON_SCALARS: st.SearchStrategy[str | int | bool | None] = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.text(max_size=20),
)
_WRONG_INTEGER_TYPES: st.SearchStrategy[str | float | bool | None] = st.one_of(
    st.none(),
    st.booleans(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(max_size=20),
)


@pytest.mark.property
@given(_EXTRA_NAMES, _JSON_SCALARS)
@settings(max_examples=40, deadline=None)
def test_unknown_schema_fields_always_fail_closed(
    extra_name: str,
    extra_value: str | int | bool | None,
) -> None:
    payload: dict[str, object] = {
        "identifier": "synthetic",
        "enabled": True,
        "count": 1,
        extra_name: extra_value,
    }

    with pytest.raises(ValidationError):
        _SchemaProbe.model_validate(payload)


@pytest.mark.property
@given(_WRONG_INTEGER_TYPES)
@settings(max_examples=40, deadline=None)
def test_strict_integer_field_never_coerces_other_types(
    wrong_count: str | float | bool | None,
) -> None:
    with pytest.raises(ValidationError):
        _SchemaProbe.model_validate(
            {"identifier": "synthetic", "enabled": True, "count": wrong_count}
        )
