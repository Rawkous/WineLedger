# Pydantic models — REST + WebSocket contracts (stable JSON via model_dump(mode="json"))

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from .models import Block, SupplyChainEvent


class LocationSchema(BaseModel):
    lat: float = Field(..., description="WGS84 latitude")
    lon: float = Field(..., description="WGS84 longitude")


class SupplyChainEventSchema(BaseModel):
    event_id: str
    event_type: str
    timestamp: datetime
    location: LocationSchema
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BlockSchema(BaseModel):
    index: int
    timestamp: datetime
    event: SupplyChainEventSchema
    previous_hash: str
    hash: str
    nonce: int = 0


class VisualParamsSchema(BaseModel):
    hue: float = Field(..., ge=0, le=360)
    saturation: float = Field(..., ge=0, le=1)
    brightness: float = Field(..., ge=0, le=1)
    motion: float = Field(..., ge=0, le=1)
    particle_burst: int = Field(..., ge=0)
    label: str


class BlockPayloadSchema(BaseModel):
    """Single block plus derived visuals — WebSocket and REST detail views."""

    block: BlockSchema
    visual: VisualParamsSchema


class SimulateOnceResponseSchema(BaseModel):
    valid_chain: bool
    blocks: List[BlockPayloadSchema]


class ChainResponseSchema(BaseModel):
    valid_chain: bool
    blocks: List[BlockPayloadSchema]


class WebSocketBlockMessageSchema(BaseModel):
    type: Literal["block"] = "block"
    payload: BlockPayloadSchema


class WebSocketChainSnapshotSchema(BaseModel):
    type: Literal["chain_snapshot"] = "chain_snapshot"
    valid_chain: bool
    blocks: List[BlockPayloadSchema]


def supply_chain_event_to_schema(ev: SupplyChainEvent) -> SupplyChainEventSchema:
    return SupplyChainEventSchema(
        event_id=ev.event_id,
        event_type=ev.event_type,
        timestamp=ev.timestamp,
        location=LocationSchema(lat=ev.location["lat"], lon=ev.location["lon"]),
        metadata=dict(ev.metadata),
    )


def block_to_schema(block: Block) -> BlockSchema:
    return BlockSchema(
        index=block.index,
        timestamp=block.timestamp,
        event=supply_chain_event_to_schema(block.event),
        previous_hash=block.previous_hash,
        hash=block.hash,
        nonce=block.nonce,
    )


def event_json_dict(ev: SupplyChainEvent) -> Dict[str, Any]:
    return supply_chain_event_to_schema(ev).model_dump(mode="json")


def block_json_dict(block: Block) -> Dict[str, Any]:
    return block_to_schema(block).model_dump(mode="json")


def stable_json(obj: BaseModel) -> str:
    """JSON string with consistent datetime encoding for wire logging."""
    return obj.model_dump_json()
