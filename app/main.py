import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .geo_enrichment import GeoEnrichmentService, SqliteGeoCache
from .persistence import PersistentBlockchain
from .mapping import event_to_visual_params
from .schemas import BlockPayloadSchema, ChainResponseSchema, SimulateOnceResponseSchema, block_to_schema
from .simulator import simulate_supply_chain
from .websocket import block_message_payload, manager, router as ws_router

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CACHE_PATH = _DATA_DIR / "geo_cache.sqlite"
_CHAIN_PATH = Path(os.environ.get("WINLEDGER_CHAIN_PATH", str(_DATA_DIR / "chain.json")))

app = FastAPI(title="WineLedger", version="0.1.0")
app.state.blockchain = PersistentBlockchain(_CHAIN_PATH)
app.state.geo = GeoEnrichmentService(cache=SqliteGeoCache(_CACHE_PATH))

app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/chain")
def get_chain(request: Request) -> dict:
    blockchain = request.app.state.blockchain
    items = []
    for b in blockchain.chain:
        vis = event_to_visual_params(b.event)
        items.append(BlockPayloadSchema(block=block_to_schema(b), visual=vis).model_dump(mode="json"))
    return ChainResponseSchema(valid_chain=blockchain.is_valid(), blocks=items).model_dump(mode="json")


@app.get("/simulate-once")
async def simulate_once(request: Request) -> dict:
    blockchain = request.app.state.blockchain
    geo = request.app.state.geo
    events = simulate_supply_chain()
    out = []
    for event in events:
        prev = blockchain.chain[-1].event
        prev_loc = None if prev.event_type == "GENESIS" else prev.location
        enriched = geo.enrich(event, prev_loc)
        block = blockchain.add_block(enriched)
        await manager.broadcast_json(block_message_payload(block))
        vis = event_to_visual_params(block.event)
        out.append(BlockPayloadSchema(block=block_to_schema(block), visual=vis).model_dump(mode="json"))
    return SimulateOnceResponseSchema(valid_chain=blockchain.is_valid(), blocks=out).model_dump(mode="json")
