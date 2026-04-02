# Blockchain logic
import hashlib
from datetime import datetime
from typing import List
from .models import Block, SupplyChainEvent

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis_event = SupplyChainEvent(
            event_id="GENESIS",
            event_type="GENESIS",
            timestamp=datetime.utcnow(),
            location={"lat": 0.0, "lon": 0.0},
            metadata={}
        )
        genesis_block = Block(
            index=0,
            timestamp=datetime.utcnow(),
            event=genesis_event,
            previous_hash="0",
            hash="",
        )
        genesis_block.hash = self._calculate_hash(genesis_block)
        self.chain.append(genesis_block)

    def _calculate_hash(self, block: Block) -> str:
        block_string = f"{block.index}{block.timestamp}{block.event.event_id}{block.previous_hash}{block.nonce}"
        return hashlib.sha256(block_string.encode("utf-8")).hexdigest()

    def add_block(self, event: SupplyChainEvent) -> Block:
        previous_block = self.chain[-1]
        new_block = Block(
            index=previous_block.index + 1,
            timestamp=datetime.utcnow(),
            event=event,
            previous_hash=previous_block.hash,
            hash="",
        )
        new_block.hash = self._calculate_hash(new_block)
        self.chain.append(new_block)
        return new_block

    def is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.previous_hash != prev.hash:
                return False
            if self._calculate_hash(curr) != curr.hash:
                return False
        return True
