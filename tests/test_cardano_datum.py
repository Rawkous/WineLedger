from datetime import datetime, timezone

import pytest

from app.blockchain import Blockchain
from app.cardano.datum import (
    EventDatum,
    TransitionError,
    build_event_datum,
    validate_transition,
)
from app.models import SupplyChainEvent


def _event(event_type: str, *, event_id: str = "e1") -> SupplyChainEvent:
    return SupplyChainEvent(
        event_id=event_id,
        event_type=event_type,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        location={"lat": 38.3, "lon": -122.3},
        metadata={"temperature": 12.0},
    )


def test_validate_transition_allows_full_cycle():
    sequence = [
        (None, "HARVEST"),
        ("HARVEST", "FERMENTATION"),
        ("FERMENTATION", "BARREL_AGING"),
        ("BARREL_AGING", "BOTTLING"),
        ("BOTTLING", "TRANSPORT"),
        ("TRANSPORT", "RETAIL"),
        ("RETAIL", "HARVEST"),
    ]
    for prev, nxt in sequence:
        validate_transition(prev, nxt)


def test_validate_transition_rejects_skip():
    with pytest.raises(TransitionError):
        validate_transition("HARVEST", "BOTTLING")


def test_validate_transition_rejects_unknown_previous():
    with pytest.raises(TransitionError):
        validate_transition("PRESS", "BOTTLING")


def test_build_event_datum_round_trip_and_hash_is_deterministic():
    bc = Blockchain()
    bc.add_block(_event("HARVEST", event_id="abc"))
    block = bc.chain[-1]

    datum_a = build_event_datum(block, ref_token="LOT-1")
    datum_b = build_event_datum(block, ref_token="LOT-1")
    assert isinstance(datum_a, EventDatum)
    assert datum_a.content_hash() == datum_b.content_hash()
    assert len(datum_a.content_hash()) == 64

    payload = datum_a.to_json()
    assert payload["ref_token"] == "LOT-1"
    assert payload["block_index"] == 1
    assert payload["event"]["event_type"] == "HARVEST"
    assert payload["event"]["location"] == {"lat": 38.3, "lon": -122.3}
    assert payload["version"] == 1


def test_build_event_datum_changes_hash_when_metadata_changes():
    bc = Blockchain()
    bc.add_block(_event("HARVEST", event_id="abc"))
    base = build_event_datum(bc.chain[-1], ref_token="LOT-1")

    bc2 = Blockchain()
    altered = _event("HARVEST", event_id="abc")
    altered.metadata["temperature"] = 13.0
    bc2.add_block(altered)
    other = build_event_datum(bc2.chain[-1], ref_token="LOT-1")
    assert base.content_hash() != other.content_hash()


def test_build_event_datum_rejects_unknown_event_type():
    bc = Blockchain()
    weird = _event("PRESS", event_id="abc")
    bc.add_block(weird)
    with pytest.raises(ValueError):
        build_event_datum(bc.chain[-1], ref_token="LOT-1")
