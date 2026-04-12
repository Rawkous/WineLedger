from datetime import datetime

from app.models import SupplyChainEvent
from app.persistence import PersistentBlockchain, load_chain, save_chain


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
