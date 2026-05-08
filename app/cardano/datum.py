"""CIP-68-shaped datum for WineLedger supply-chain events.

The :class:`EventDatum` is a JSON-shaped projection of what a real Plutus
datum would look like once encoded as CBOR by an off-chain tx-builder.
Keeping the projection in pure Python lets us:

* validate stage transitions before we ever touch a sidecar,
* compute a deterministic content hash that doubles as a stable
  ``tx_id`` in :class:`~app.cardano.tx_builder.DryRunTxBuilder`, and
* unit-test the integration without a Cardano node.

The matching rules a real Aiken/Plutus validator would enforce are
captured by :func:`validate_transition`.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from ..models import Block, SupplyChainEvent
from ..simulator import EVENT_SEQUENCE


CIP68_VERSION = 1
"""Datum schema version. Bump when the on-chain shape changes."""


GENESIS_EVENT_TYPE = "GENESIS"


_VALID_TRANSITIONS: Dict[Optional[str], frozenset[str]] = {
    None: frozenset({"HARVEST"}),
    GENESIS_EVENT_TYPE: frozenset({"HARVEST"}),
    "HARVEST": frozenset({"FERMENTATION"}),
    "FERMENTATION": frozenset({"BARREL_AGING"}),
    "BARREL_AGING": frozenset({"BOTTLING"}),
    "BOTTLING": frozenset({"TRANSPORT"}),
    "TRANSPORT": frozenset({"RETAIL"}),
    "RETAIL": frozenset({"HARVEST"}),
}


class TransitionError(ValueError):
    """Raised when a supply-chain stage transition is not allowed."""


def validate_transition(prev_event_type: Optional[str], next_event_type: str) -> None:
    """Validate that ``next_event_type`` may follow ``prev_event_type``.

    Mirrors the constraint a Plutus validator would enforce on-chain so
    bad inputs fail fast in Python before a sidecar is invoked. ``None``
    or ``"GENESIS"`` represent an empty / fresh chain.
    """

    allowed = _VALID_TRANSITIONS.get(prev_event_type)
    if allowed is None:
        raise TransitionError(
            f"Unknown previous stage {prev_event_type!r}; expected one of "
            f"{sorted(s for s in _VALID_TRANSITIONS if s)} or None."
        )
    if next_event_type not in allowed:
        raise TransitionError(
            f"Stage {next_event_type!r} cannot follow {prev_event_type!r}; "
            f"allowed next stages: {sorted(allowed)}."
        )


@dataclass(frozen=True)
class EventDatum:
    """JSON projection of a CIP-68 datum carrying a single event.

    Real CIP-68 datums use a Plutus ``Constr`` with a metadata map and a
    version integer; the same logical content is encoded here as JSON so
    it round-trips through the FastAPI layer and out to a sidecar.
    """

    ref_token: str
    block_index: int
    previous_hash: str
    block_hash: str
    event: Dict[str, Any]
    version: int = CIP68_VERSION
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return {
            "ref_token": self.ref_token,
            "block_index": self.block_index,
            "previous_hash": self.previous_hash,
            "block_hash": self.block_hash,
            "event": dict(self.event),
            "version": self.version,
            "extra": dict(self.extra),
        }

    def canonical_json(self) -> str:
        """Stable serialisation used for content hashing.

        ``sort_keys`` and tight separators keep the hash insensitive to
        Python dict ordering and whitespace. The same string is what a
        sidecar would CBOR-encode into the on-chain datum.
        """

        return json.dumps(self.to_json(), sort_keys=True, separators=(",", ":"))

    def content_hash(self) -> str:
        """SHA-256 over :meth:`canonical_json` — used as a fake tx id."""

        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def _event_to_payload(event: SupplyChainEvent) -> Dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "location": {
            "lat": float(event.location["lat"]),
            "lon": float(event.location["lon"]),
        },
        "metadata": dict(event.metadata),
    }


def build_event_datum(
    block: Block,
    *,
    ref_token: str,
    extra: Optional[Mapping[str, Any]] = None,
) -> EventDatum:
    """Project a :class:`Block` into an :class:`EventDatum`.

    The datum is what a real CIP-68 update would carry off-chain to the
    Hydra head; ``ref_token`` is the long-lived bottle/batch identity
    while the inner event captures the current state transition.
    """

    if block.event.event_type not in EVENT_SEQUENCE and block.event.event_type != GENESIS_EVENT_TYPE:
        raise ValueError(
            f"Refusing to build datum for unknown event_type={block.event.event_type!r}"
        )

    return EventDatum(
        ref_token=ref_token,
        block_index=block.index,
        previous_hash=block.previous_hash,
        block_hash=block.hash,
        event=_event_to_payload(block.event),
        extra=dict(extra or {}),
    )
