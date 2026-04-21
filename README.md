# WineLedger

**WineLedger** is a blockchain-inspired, web-based digital twin of the wine supply chain that transforms every step of a bottle’s journey—from vineyard to glass—into **living generative art**. The system simulates a realistic supply chain, records each event (harvest, fermentation, barrel aging, bottling, transport, retail) on a lightweight blockchain ledger, and streams those events to a browser-based visual engine. Each event becomes a visual gesture: a burst of particles, a shift in color, a change in motion—so transparency, sustainability, and “health” become something you can see evolving over time.

Built at the intersection of blockchain, supply chain modeling, and creative coding, WineLedger is both an educational tool and an artistic exploration of how data can tell stories. Under the hood, the FastAPI layer stays thin (REST + WebSockets) while events can be enriched with geography metadata (routing hints, region codes, and NDR-style geometry references) using a pluggable cache. The **chain is persisted** to disk (JSON under `data/`) so restarts keep history; as you scale, heavier batch work can move to **NRP** compute, and durable shared datasets or artifacts can land in an **NDR** data tier—without changing the core event and ledger contract.

## Repository layout

```
WineLedger/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI entrypoint, REST routes
│   ├── models.py            # Block, SupplyChainEvent dataclasses
│   ├── schemas.py           # Pydantic models (REST + WebSocket JSON)
│   ├── blockchain.py        # Chain logic
│   ├── persistence.py       # JSON chain file + PersistentBlockchain
│   ├── simulator.py         # Synthetic supply chain events
│   ├── mapping.py           # Event → visual parameters
│   ├── geo_enrichment.py    # Geo adapter + cache + NDR-ready interface
│   └── websocket.py         # WebSocket `/ws` + broadcast helpers
├── tests/
│   ├── conftest.py          # test-only chain path isolation
│   ├── test_blockchain.py
│   ├── test_api.py
│   ├── test_geo.py
│   └── test_persistence.py
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
├── data/                    # gitignored: geo cache, chain JSON (see below)
├── Makefile                 # install / test / dev helpers
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
- Run Uvicorn + Vite on your machine. Geo cache uses `data/geo_cache.sqlite`; the chain is stored at `data/chain.json` (created automatically).

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

**Quick start (Make)** — requires [GNU Make](https://www.gnu.org/software/make/) (e.g. Git Bash or WSL on Windows):

```bash
cd WineLedger
make install
make test
# Terminal 1:
make dev-backend
# Terminal 2:
make dev-frontend
```

See `make help` for targets.

If you’re on a system with globally-installed pytest plugins (common with ROS), `make test` disables external plugin autoload by default for repeatability. To re-enable it:

```bash
make PYTEST_DISABLE_PLUGIN_AUTOLOAD=0 test
```

**Backend** (manual)

```bash
cd WineLedger
python3 -m pip install -r requirements.txt
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

- **Chain file**: Default path is `data/chain.json`. Override with environment variable `WINLEDGER_CHAIN_PATH` (absolute path to a `.json` file). Tests set this automatically to a temp file so they do not touch your dev chain.
- **Geo API keys**: For future OSM or vendor routing APIs, use environment variables or your campus secret store; do not commit secrets.
- **Geo cache path**: `GeoEnrichmentService` uses `SqliteGeoCache` at `data/geo_cache.sqlite` (created automatically).

## License

See project policy for your institution or add a license file when you publish.
