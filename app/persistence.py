# Persist the chain to disk (JSON). Timestamps round-trip via str()/fromisoformat() to keep hashes valid.

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .blockchain import Blockchain
from .models import Block, SupplyChainEvent


def _dt_from_str(s: str) -> datetime:
    return datetime.fromisoformat(s)


def _block_to_record(block: Block) -> Dict[str, Any]:
    return {
        "index": block.index,
        "timestamp": str(block.timestamp),
        "event": _event_to_record(block.event),
        "previous_hash": block.previous_hash,
        "hash": block.hash,
        "nonce": block.nonce,
    }


def _event_to_record(ev: SupplyChainEvent) -> Dict[str, Any]:
    return {
        "event_id": ev.event_id,
        "event_type": ev.event_type,
        "timestamp": str(ev.timestamp),
        "location": {"lat": ev.location["lat"], "lon": ev.location["lon"]},
        "metadata": dict(ev.metadata),
    }


def _record_to_block(d: Dict[str, Any]) -> Block:
    ev = _record_to_event(d["event"])
    return Block(
        index=int(d["index"]),
        timestamp=_dt_from_str(d["timestamp"]),
        event=ev,
        previous_hash=str(d["previous_hash"]),
        hash=str(d["hash"]),
        nonce=int(d.get("nonce", 0)),
    )


def _record_to_event(d: Dict[str, Any]) -> SupplyChainEvent:
    loc = d["location"]
    return SupplyChainEvent(
        event_id=str(d["event_id"]),
        event_type=str(d["event_type"]),
        timestamp=_dt_from_str(d["timestamp"]),
        location={"lat": float(loc["lat"]), "lon": float(loc["lon"])},
        metadata=dict(d.get("metadata") or {}),
    )


def save_chain(path: Path, chain: List[Block]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "blocks": [_block_to_record(b) for b in chain],
    }
    text = json.dumps(payload, indent=2, sort_keys=False)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def load_chain(path: Path) -> Optional[List[Block]]:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    data = json.loads(raw)
    blocks = [_record_to_block(b) for b in data["blocks"]]
    return blocks


class PersistentBlockchain(Blockchain):
    """Loads/saves the full chain after each new block (atomic JSON write)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        loaded = load_chain(path)
        if loaded is not None:
            self.chain = loaded
            if not self.is_valid():
                raise ValueError(f"Invalid or corrupt chain file: {path}")
        else:
            self.chain = []
            self._create_genesis_block()
            self._persist()

    def _persist(self) -> None:
        save_chain(self._path, self.chain)

    def add_block(self, event: SupplyChainEvent) -> Block:
        block = super().add_block(event)
        self._persist()
        return block
