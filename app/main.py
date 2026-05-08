import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .cardano import HydraBridge, HydraSubmission, load_cardano_settings
from .geo_enrichment import GeoEnrichmentService, SqliteGeoCache
from .persistence import PersistentBlockchain
from .mapping import event_to_visual_params
from .schemas import (
    BlockPayloadSchema,
    CardanoSubmissionSchema,
    ChainResponseSchema,
    SimulateOnceResponseSchema,
    block_to_schema,
)
from .simulator import simulate_supply_chain
from .websocket import block_message_payload, manager, router as ws_router


logging.basicConfig(level=os.environ.get("WINELEDGER_LOG_LEVEL", "INFO"))

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CACHE_PATH = _DATA_DIR / "geo_cache.sqlite"
_CHAIN_PATH = Path(os.environ.get("WINLEDGER_CHAIN_PATH", str(_DATA_DIR / "chain.json")))
_SUBMISSIONS_PATH = _DATA_DIR / "cardano_submissions.json"

_cardano_settings = load_cardano_settings(default_submissions_path=_SUBMISSIONS_PATH)

app = FastAPI(title="WineLedger", version="0.1.0")
app.state.blockchain = PersistentBlockchain(_CHAIN_PATH)
app.state.geo = GeoEnrichmentService(cache=SqliteGeoCache(_CACHE_PATH))
app.state.cardano_bridge = HydraBridge.from_settings(_cardano_settings)

app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _submission_to_schema(submission: Optional[HydraSubmission]) -> Optional[CardanoSubmissionSchema]:
    if submission is None:
        return None
    return CardanoSubmissionSchema(**submission.to_payload())


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/chain")
def get_chain(request: Request) -> dict:
    blockchain = request.app.state.blockchain
    bridge: HydraBridge = request.app.state.cardano_bridge
    items = []
    for b in blockchain.chain:
        vis = event_to_visual_params(b.event)
        record = bridge.store.get(b.event.event_id)
        cardano: Optional[CardanoSubmissionSchema] = None
        if record is not None:
            cardano = CardanoSubmissionSchema(
                event_id=record.event_id,
                block_index=record.block_index,
                block_hash=record.block_hash,
                tx_id=record.tx_id,
                status=record.status,
                mode=record.mode,
                head_id=record.head_id,
                error=record.error,
                submitted_at=record.submitted_at,
            )
        items.append(
            BlockPayloadSchema(
                block=block_to_schema(b),
                visual=vis,
                cardano=cardano,
            ).model_dump(mode="json")
        )
    return ChainResponseSchema(valid_chain=blockchain.is_valid(), blocks=items).model_dump(mode="json")


@app.get("/simulate-once")
async def simulate_once(
    request: Request,
    pace_ms: int = Query(
        default=0,
        ge=0,
        le=120_000,
        description="Pause between each supply-chain event (ms) so WebSocket clients can show visuals longer.",
    ),
) -> dict:
    blockchain = request.app.state.blockchain
    geo = request.app.state.geo
    bridge: HydraBridge = request.app.state.cardano_bridge
    events = simulate_supply_chain()
    out = []
    pace_sec = pace_ms / 1000.0
    for i, event in enumerate(events):
        prev = blockchain.chain[-1].event
        prev_loc = None if prev.event_type == "GENESIS" else prev.location
        enriched = geo.enrich(event, prev_loc)
        block = blockchain.add_block(enriched)
        submission = await bridge.submit_block(block, prev_event_type=prev.event_type)
        cardano_schema = _submission_to_schema(submission)
        await manager.broadcast_json(block_message_payload(block, cardano=cardano_schema))
        vis = event_to_visual_params(block.event)
        out.append(
            BlockPayloadSchema(
                block=block_to_schema(block),
                visual=vis,
                cardano=cardano_schema,
            ).model_dump(mode="json")
        )
        if pace_sec > 0 and i < len(events) - 1:
            await asyncio.sleep(pace_sec)
    return SimulateOnceResponseSchema(valid_chain=blockchain.is_valid(), blocks=out).model_dump(mode="json")


@app.get("/cardano/status")
async def cardano_status(request: Request) -> Dict[str, Any]:
    bridge: HydraBridge = request.app.state.cardano_bridge
    return await bridge.status()


@app.get("/cardano/submissions")
def cardano_submissions(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> Dict[str, Any]:
    bridge: HydraBridge = request.app.state.cardano_bridge
    items = [r.to_json() for r in bridge.store.list(limit=limit)]
    return {"count": len(items), "submissions": items}


@app.get("/cardano/submissions/{event_id}")
def cardano_submission(request: Request, event_id: str) -> Dict[str, Any]:
    bridge: HydraBridge = request.app.state.cardano_bridge
    record = bridge.store.get(event_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No submission for event_id={event_id}")
    return record.to_json()


@app.post("/cardano/dryrun")
async def cardano_dryrun(request: Request) -> Dict[str, Any]:
    """Build the next event datum without submitting anything.

    Useful for classroom demos and integration testing — pulls the most
    recent block from the local chain and returns the CIP-68-shaped
    datum the bridge would have submitted in ``dryrun`` mode.
    """

    blockchain = request.app.state.blockchain
    bridge: HydraBridge = request.app.state.cardano_bridge
    if not blockchain.chain:
        raise HTTPException(status_code=409, detail="Chain is empty")
    block = blockchain.chain[-1]
    if block.event.event_type == "GENESIS":
        raise HTTPException(status_code=409, detail="Only the genesis block exists; run /simulate-once first")
    datum = await bridge.preview(block)
    return {
        "block_index": block.index,
        "event_id": block.event.event_id,
        "datum": datum.to_json(),
        "content_hash": datum.content_hash(),
    }
