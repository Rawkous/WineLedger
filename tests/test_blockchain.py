from app.blockchain import Blockchain
from app.models import SupplyChainEvent
from app.schemas import block_to_schema, supply_chain_event_to_schema
from datetime import datetime


def test_genesis_and_add_block():
    bc = Blockchain()
    assert len(bc.chain) == 1
    assert bc.chain[0].event.event_type == "GENESIS"
    ev = SupplyChainEvent(
        event_id="e1",
        event_type="HARVEST",
        timestamp=datetime.utcnow(),
        location={"lat": 38.3, "lon": -122.3},
        metadata={"temperature": 12.0},
    )
    b = bc.add_block(ev)
    assert b.index == 1
    assert bc.is_valid()


def test_chain_invalid_if_tampered():
    bc = Blockchain()
    ev = SupplyChainEvent(
        event_id="e1",
        event_type="HARVEST",
        timestamp=datetime.utcnow(),
        location={"lat": 38.3, "lon": -122.3},
        metadata={},
    )
    bc.add_block(ev)
    bc.chain[1].hash = "deadbeef"
    assert not bc.is_valid()


def test_schema_roundtrip_json_keys():
    bc = Blockchain()
    schema = block_to_schema(bc.chain[0])
    d = schema.model_dump(mode="json")
    assert "timestamp" in d
    assert "event" in d
    assert "location" in d["event"]
    assert set(d["event"]["location"].keys()) == {"lat", "lon"}


def test_supply_chain_event_schema():
    ev = SupplyChainEvent(
        event_id="x",
        event_type="RETAIL",
        timestamp=datetime.utcnow(),
        location={"lat": 1.0, "lon": 2.0},
        metadata={"a": 1},
    )
    s = supply_chain_event_to_schema(ev)
    assert s.model_dump(mode="json")["metadata"]["a"] == 1
