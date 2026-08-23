"""Canonical serialization, hashing, and component-local random generators."""

import hashlib
import json
from collections.abc import Mapping
from datetime import date, datetime, time
from enum import Enum
from pathlib import Path
from typing import cast

import numpy as np
from pydantic import BaseModel

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]


def _canonical_sort_key(value: object) -> str:
    return json.dumps(
        _to_json_value(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _to_json_value(value: object) -> JsonValue:
    if isinstance(value, BaseModel):
        return _to_json_value(value.model_dump(mode="python", round_trip=True))
    if isinstance(value, Enum):
        return _to_json_value(value.value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Mapping):
        normalized: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical mappings require string keys")
            normalized[key] = _to_json_value(item)
        return normalized
    if isinstance(value, (set, frozenset)):
        return [_to_json_value(item) for item in sorted(value, key=_canonical_sort_key)]
    if isinstance(value, (list, tuple)):
        return [_to_json_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return cast(JsonScalar, value)
    if isinstance(value, float):
        return 0.0 if value == 0.0 else value
    raise TypeError(f"unsupported canonical value type: {type(value).__name__}")


def canonical_json(value: object) -> str:
    """Return compact UTF-8 JSON with deterministic ordering and no NaN values."""

    return json.dumps(
        _to_json_value(value),
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def canonical_json_bytes(value: object) -> bytes:
    """Return the canonical representation encoded as UTF-8."""

    return canonical_json(value).encode("utf-8")


def canonical_sha256(value: object) -> str:
    """Hash a value's canonical representation with SHA-256."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def verify_canonical_sha256(value: object, expected_digest: str) -> bool:
    """Compare a canonical digest without accepting malformed digest strings."""

    if len(expected_digest) != 64:
        return False
    try:
        bytes.fromhex(expected_digest)
    except ValueError:
        return False
    return canonical_sha256(value) == expected_digest.lower()


def derive_component_seed(run_seed: int, namespace: str) -> int:
    """Derive a stable unsigned 64-bit seed for one component namespace."""

    if isinstance(run_seed, bool) or not isinstance(run_seed, int) or run_seed < 0:
        raise ValueError("run_seed must be a non-negative integer")
    if not namespace:
        raise ValueError("namespace must not be empty")
    material = canonical_json_bytes(
        {
            "domain": "pacd-simulation/component-seed/v1",
            "namespace": namespace,
            "run_seed": run_seed,
        }
    )
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big", signed=False)


def create_rng(run_seed: int, namespace: str) -> np.random.Generator:
    """Create an isolated NumPy generator; ambient global RNG state is never used."""

    return np.random.default_rng(derive_component_seed(run_seed, namespace))
