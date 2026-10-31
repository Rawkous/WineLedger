# Blockchain logic
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List
from .models import Block, SupplyChainEvent

# v1 hashed only index/timestamp/event_id/previous_hash/nonce, so edits to an
# event's type, location, or metadata went undetected. v2 hashes everything.
HASH_VERSION = 2


def _event_hash_payload(event: SupplyChainEvent) -> Dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "location": {"lat": float(event.location["lat"]), "lon": float(event.location["lon"])},
        "metadata": event.metadata,
    }


def calculate_block_hash(block: Block) -> str:
    """SHA-256 over canonical JSON of the full block (minus its own hash)."""
    payload = {
        "index": block.index,
        "timestamp": block.timestamp.isoformat(),
        "event": _event_hash_payload(block.event),
        "previous_hash": block.previous_hash,
        "nonce": block.nonce,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def legacy_block_hash(block: Block) -> str:
    """v1 hash — only used to verify chain files written before HASH_VERSION 2."""
    block_string = f"{block.index}{block.timestamp}{block.event.event_id}{block.previous_hash}{block.nonce}"
    return hashlib.sha256(block_string.encode("utf-8")).hexdigest()


def chain_is_valid(chain: List[Block], hash_fn: Callable[[Block], str] = calculate_block_hash) -> bool:
    for i, curr in enumerate(chain):
        if hash_fn(curr) != curr.hash:
            return False
        if i > 0 and curr.previous_hash != chain[i - 1].hash:
            return False
    return True


class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis_event = SupplyChainEvent(
            event_id="GENESIS",
            event_type="GENESIS",
            timestamp=datetime.now(timezone.utc),
            location={"lat": 0.0, "lon": 0.0},
            metadata={}
        )
        genesis_block = Block(
            index=0,
            timestamp=datetime.now(timezone.utc),
            event=genesis_event,
            previous_hash="0",
            hash="",
        )
        genesis_block.hash = self._calculate_hash(genesis_block)
        self.chain.append(genesis_block)

    def _calculate_hash(self, block: Block) -> str:
        return calculate_block_hash(block)

    def add_block(self, event: SupplyChainEvent) -> Block:
        previous_block = self.chain[-1]
        new_block = Block(
            index=previous_block.index + 1,
            timestamp=datetime.now(timezone.utc),
            event=event,
            previous_hash=previous_block.hash,
            hash="",
        )
        new_block.hash = self._calculate_hash(new_block)
        self.chain.append(new_block)
        return new_block

    def is_valid(self) -> bool:
        return chain_is_valid(self.chain)
