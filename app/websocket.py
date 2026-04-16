# WebSocket endpoints — JSON messages use schemas for stable serialization

from __future__ import annotations

import json
from typing import Any, List

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from .blockchain import Blockchain
from .models import Block
from .mapping import event_to_visual_params
from .schemas import (
    BlockPayloadSchema,
    WebSocketBlockMessageSchema,
    WebSocketChainSnapshotSchema,
    block_to_schema,
)

router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast_json(self, payload: Any) -> None:
        text = json.dumps(payload, default=str)
        for ws in list(self.active):
            try:
                await ws.send_text(text)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


def chain_snapshot_payload(blockchain: Blockchain) -> dict:
    items = []
    for b in blockchain.chain:
        vis = event_to_visual_params(b.event)
        items.append(BlockPayloadSchema(block=block_to_schema(b), visual=vis).model_dump(mode="json"))
    return WebSocketChainSnapshotSchema(
        valid_chain=blockchain.is_valid(),
        blocks=items,
    ).model_dump(mode="json")


def block_message_payload(block: Block) -> dict:
    vis = event_to_visual_params(block.event)
    return WebSocketBlockMessageSchema(
        payload=BlockPayloadSchema(block=block_to_schema(block), visual=vis),
    ).model_dump(mode="json")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    blockchain: Blockchain = websocket.app.state.blockchain
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps(chain_snapshot_payload(blockchain), default=str))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
