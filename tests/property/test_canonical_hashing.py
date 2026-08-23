"""Property checks for deterministic canonical serialization and hashing."""

from __future__ import annotations

import json
import math
import re
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pacd_sim.reproducibility.canonical import canonical_json_bytes, canonical_sha256

_JSON_SCALAR: st.SearchStrategy[str | int | bool | None] = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-(2**53), max_value=2**53),
    st.text(alphabet=st.characters(min_codepoint=0x20, max_codepoint=0x7E), max_size=24),
)
_JSON_VALUE = st.recursive(
    _JSON_SCALAR,
    lambda children: (
        st.lists(children, max_size=5)
        | st.dictionaries(st.text(min_size=1, max_size=12), children, max_size=5)
    ),
    max_leaves=20,
)


@pytest.mark.property
@given(st.dictionaries(st.text(min_size=1, max_size=12), _JSON_VALUE, max_size=8))
@settings(max_examples=50, deadline=None)
def test_mapping_insertion_order_does_not_change_canonical_hash(value: dict[str, Any]) -> None:
    reordered = dict(reversed(tuple(value.items())))

    assert canonical_json_bytes(value) == canonical_json_bytes(reordered)
    assert canonical_sha256(value) == canonical_sha256(reordered)
    assert json.loads(canonical_json_bytes(value)) == value


@pytest.mark.property
@given(_JSON_VALUE)
@settings(max_examples=50, deadline=None)
def test_canonical_hash_is_stable_and_well_formed(value: Any) -> None:
    first = canonical_sha256(value)

    assert first == canonical_sha256(value)
    assert re.fullmatch(r"[0-9a-f]{64}", first)


@pytest.mark.property
@given(st.integers(), st.integers())
def test_sequence_order_remains_semantically_significant(left: int, right: int) -> None:
    if left == right:
        return

    assert canonical_sha256([left, right]) != canonical_sha256([right, left])


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_not_canonicalizable(value: float) -> None:
    with pytest.raises((TypeError, ValueError)):
        canonical_json_bytes({"unsafe_number": value})
