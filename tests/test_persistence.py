import json
from datetime import datetime

import pytest

from app.blockchain import Blockchain, legacy_block_hash
from app.models import SupplyChainEvent
from app.persistence import CHAIN_FILE_VERSION, PersistentBlockchain, load_chain, save_chain


def test_save_load_roundtrip_preserves_validity(tmp_path):
    chain_path = tmp_path / "chain.json"
    bc = PersistentBlockchain(chain_path)
    assert bc.is_valid()
    ev = SupplyChainEvent(
        event_id="e1",
        event_type="HARVEST",
        timestamp=datetime.utcnow(),
        location={"lat": 38.3, "lon": -122.3},
        metadata={"k": 1},
    )
    bc.add_block(ev)
    assert bc.is_valid()

    bc2 = PersistentBlockchain(chain_path)
    assert len(bc2.chain) == len(bc.chain)
    assert bc2.is_valid()
    assert bc2.chain[-1].event.event_type == "HARVEST"


def test_load_missing_file_creates_genesis(tmp_path):
    chain_path = tmp_path / "chain.json"
    assert not chain_path.exists()
    bc = PersistentBlockchain(chain_path)
    assert len(bc.chain) == 1
    assert bc.chain[0].event.event_type == "GENESIS"
    assert chain_path.exists()


def test_save_chain_and_load_chain(tmp_path):
    chain_path = tmp_path / "chain.json"
    from app.blockchain import Blockchain

    bc = Blockchain()
    save_chain(chain_path, bc.chain)
    loaded = load_chain(chain_path)
    assert len(loaded) == 1
    assert loaded[0].hash == bc.chain[0].hash


def _harvest_event(metadata=None):
    return SupplyChainEvent(
        event_id="e1",
        event_type="HARVEST",
        timestamp=datetime.utcnow(),
        location={"lat": 38.3, "lon": -122.3},
        metadata=metadata if metadata is not None else {"temperature": 12.0, "route_km": 4.123},
    )


def test_tampered_metadata_on_disk_is_rejected(tmp_path):
    chain_path = tmp_path / "chain.json"
    PersistentBlockchain(chain_path).add_block(_harvest_event())

    data = json.loads(chain_path.read_text())
    data["blocks"][1]["event"]["metadata"]["temperature"] = 99.0
    chain_path.write_text(json.dumps(data))

    with pytest.raises(ValueError, match="Invalid or corrupt"):
        PersistentBlockchain(chain_path)


def _write_legacy_chain(chain_path):
    bc = Blockchain()
    bc.add_block(_harvest_event())
    for i, block in enumerate(bc.chain):
        if i > 0:
            block.previous_hash = bc.chain[i - 1].hash
        block.hash = legacy_block_hash(block)
    save_chain(chain_path, bc.chain)
    data = json.loads(chain_path.read_text())
    data["version"] = 1
    chain_path.write_text(json.dumps(data))
    return data


def test_legacy_v1_chain_is_migrated(tmp_path):
    chain_path = tmp_path / "chain.json"
    legacy = _write_legacy_chain(chain_path)

    bc = PersistentBlockchain(chain_path)
    assert bc.is_valid()
    assert bc.chain[1].hash != legacy["blocks"][1]["hash"]
    assert json.loads(chain_path.read_text())["version"] == CHAIN_FILE_VERSION
    assert PersistentBlockchain(chain_path).is_valid()


def test_corrupt_legacy_v1_chain_is_rejected(tmp_path):
    chain_path = tmp_path / "chain.json"
    legacy = _write_legacy_chain(chain_path)
    legacy["blocks"][1]["previous_hash"] = "deadbeef"
    chain_path.write_text(json.dumps(legacy))

    with pytest.raises(ValueError, match="Invalid or corrupt"):
        PersistentBlockchain(chain_path)
