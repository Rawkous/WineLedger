# WineLedger

**WineLedger** is a blockchain-inspired, web-based digital twin of the wine supply chain that turns each step of a bottle’s journey—from vineyard to glass—into generative visuals.

The system simulates a realistic wine supply chain, records each event (harvest, fermentation, barrel aging, bottling, transport, retail) on a lightweight blockchain ledger, enriches events with geography metadata (routing hints, region codes, and NDR-style geometry references), and streams mapped payloads to a browser-based renderer. The FastAPI layer stays thin: orchestration, REST, WebSockets, and a pluggable geo cache; heavier batch work and large datasets can move to NRP/NDR as you scale.

## Repository layout

```
WineLedger/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entrypoint, REST routes
│   ├── models.py            # Block, SupplyChainEvent dataclasses
│   ├── schemas.py           # Pydantic models (REST + WebSocket JSON)
│   ├── blockchain.py        # Chain logic
│   ├── simulator.py       # Synthetic supply chain events
│   ├── mapping.py           # Event → visual parameters
│   ├── geo_enrichment.py    # Geo adapter + cache + NDR-ready interface
│   └── websocket.py         # WebSocket `/ws` + broadcast helpers
├── tests/
│   ├── test_blockchain.py
│   ├── test_api.py
│   └── test_geo.py
├── frontend/
│   ├── index.html
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.js
│       ├── renderer.js      # p5.js visuals
│       ├── websocketClient.js
│       ├── ui.js
│       └── styles.css
├── data/                    # Local SQLite geo cache (gitignored)
├── requirements.txt
├── pytest.ini
└── README.md
```

Older docs that referred to `backend/app/` described the same code; the live tree is **`app/`** at the repo root.

## CENIC AIR, NRP, and NDR (data tier)

| Layer | Role here |
|--------|-----------|
| **CENIC / CENIC AIR** | High-capacity research and education connectivity in California—well suited to **WebSocket streaming**, **map tile traffic**, and moving larger artifacts without relying only on the public internet. |
| **NRP (National Research Platform)** | Shared **compute** (CPUs/GPUs, clusters, notebooks) for batch jobs you do not want on a laptop: batch geocoding, route precomputation, scheduled cache refresh, or heavier ML later. |
| **NDR (national / durable data tier)** | **Durable, shareable data plane**: versioned reference geodata, cached third-party API responses, **ledger snapshots**, and large static assets. `GeoCacheBackend` is implemented locally first (SQLite); the same protocol can be backed by object storage or an institutional bucket when you attach NDR. |

## Deployment phases

**Phase A — Local (this repo)**  
- Run Uvicorn + Vite on your machine. Geo cache uses `data/geo_cache.sqlite` under the repo root.

**Phase B — Campus / R&E path**  
- Serve the API behind your reverse proxy on **CENIC AIR** (or equivalent) so browsers use WebSockets and REST on a stable campus host. Point NRP **cron or Kubernetes jobs** at the same enrichment pipeline to refresh regional caches or precompute routes between fixed nodes (vineyard → facility → retail).

**Phase C — NDR-backed artifacts**  
- Swap `SqliteGeoCache` for an implementation of `GeoCacheBackend` that reads/writes your **NDR** object store (S3-compatible or campus-specific). Optionally export **ledger snapshots** and provenance hashes to NDR for reproducibility across institutions.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/chain` | Full chain with `block` + `visual` per entry |
| GET | `/simulate-once` | Runs one synthetic chain segment, adds blocks, enriches geo, **broadcasts each block** on `/ws` |
| WS | `/ws` | Initial `chain_snapshot`, then `block` messages when new blocks are added |

## Local development

**Backend**

```bash
cd WineLedger
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend** (Vite proxies `/ws`, `/chain`, `/simulate-once` to port 8000)

```bash
cd frontend
npm install
npm run dev
```

Open the dev URL (default `http://127.0.0.1:5173`). Click **Simulate supply chain** or connect another client to the WebSocket to see live updates.

**Tests**

```bash
python -m pytest
```

## Configuration

- **Geo API keys**: For future OSM or vendor routing APIs, use environment variables or your campus secret store; do not commit secrets.
- **Cache path**: `GeoEnrichmentService` uses `SqliteGeoCache` at `data/geo_cache.sqlite` (created automatically).

## License

See project policy for your institution or add a license file when you publish.
