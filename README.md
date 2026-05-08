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

## Cardano platform alignment (CIP-68 + Hydra)

Proposals that assign a **unique digital identity** to each bottle or batch, record **harvest → production → distribution → sale → storage** on-chain, and rely on **immutability** for authenticity map cleanly onto what WineLedger already models: each `SupplyChainEvent` (see `app/models.py`) is an append-only step with hashes and metadata. Moving from this **local teaching chain** to Cardano would swap JSON persistence for **L1 anchors** and **standard token/metadata patterns**, while keeping the same conceptual pipeline the UI and API exercise.

| Proposal idea | In WineLedger today | On Cardano (directional) |
|---------------|---------------------|---------------------------|
| Unique ID per bottle/batch | `event_id`, block index, metadata | **CIP-68** reference token (stable identity) plus updatable “standard” representation / datum for current state |
| Frequent movements & sensor-style updates | WebSocket + `/chain`; optional future IoT fields in `metadata` | **Cardano Hydra** heads for high-rate, low-fee updates between participants, with periodic **settlement** to L1 for public auditability |
| Irrefutable authenticity narrative | Linked blocks, `previous_hash`, persisted chain | L1 immutability + explicit mint/update policies (who may attest each stage) |
| Open-source verification of storage conditions | Not implemented; extensible via `metadata` | Signed oracle / device attestations committed as metadata or follow-on events; same teaching hooks |

**CIP-68 (why it fits wine):** It separates a **long-lived reference** (the bottle/batch identity) from **mutable on-chain fields** you are allowed to update under policy—closer to supply-chain reality than a one-off static NFT image. Each WineLedger block is already a “state transition”; CIP-68 is how many teams express that pattern on Cardano without reminting identity on every scan.

**Cardano Hydra (scaling):** *Not the same as this repo’s canvas.* The browser visuals use **[Hydra Synth](https://hydra.ojack.xyz/)** (`hydra-synth`). **Cardano Hydra** is a **Layer-2 isomorphic state-channel** framework: parties run fast, cheap updates off the main chain, then commit snapshots to L1. That matches “frequent, almost zero-cost updates” for logistics and environmental reads, with L1 as the trust anchor—similar in *role* to streaming many events here before you batch-export a snapshot to NDR.

**Practical integration sketch (out of scope for the default app):** Keep FastAPI as the orchestration and simulation layer; add a **Cardano client** (e.g. Ogmios, Kupo, Blockfrost, or Pallas) to mint/update CIP-68 assets under a Plutus minting/spending policy; route bursty updates through a **Hydra head** where economics justify it; mirror or hash-link `chain.json` snapshots to **metadata** for reproducibility. The generative front end can stay as-is: it already consumes structured events—only the **source of truth** for those events would gain a Cardano-backed path.

### Bridge implementation in this repo

The `app/cardano/` package implements the bridge in three modes controlled by `WINELEDGER_HYDRA_MODE`:

| Mode | Behavior | Need a Cardano stack? |
|------|----------|------------------------|
| `disabled` (default) | No Cardano work. Existing API and tests are unchanged. | No |
| `dryrun` | Builds the CIP-68-shaped `EventDatum`, computes a deterministic `tx_id` (SHA-256 over the canonical datum JSON), and records every event in `data/cardano_submissions.json`. | No |
| `live` | Forwards the datum to a configured tx-builder sidecar (`POST /build`) and submits the returned CBOR to a Hydra node (`POST /cardano-transaction`). | Yes |

New endpoints exposed when the bridge is loaded:

- `GET /cardano/status` — current mode, network, head id, sidecar name, Hydra reachability.
- `POST /cardano/dryrun` — preview the next datum without submitting.
- `GET /cardano/submissions` and `GET /cardano/submissions/{event_id}` — durable submission history.

Operations and runbook live under `ops/cardano/`; full developer notes are in [doc/cardano-hydra.md](doc/cardano-hydra.md).

> **Hydra naming:** the browser canvas uses **Hydra Synth** (`hydra-synth`); the Cardano L2 framework is **Cardano Hydra**. Different projects, same word.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness |
| GET | `/chain` | Full chain with `block` + `visual` per entry (and `cardano` when the Hydra bridge is enabled) |
| GET | `/simulate-once` | Runs one synthetic chain segment, adds blocks, enriches geo, **broadcasts each block** on `/ws`. Optional query `pace_ms` (0–120000): pause in milliseconds **between** events so visuals stay on screen longer. |
| WS | `/ws` | Initial `chain_snapshot`, then `block` messages when new blocks are added |
| GET | `/cardano/status` | Bridge mode, network, head id, sidecar, and Hydra reachability |
| POST | `/cardano/dryrun` | Build the CIP-68-shaped datum for the latest block — no submission |
| GET | `/cardano/submissions` | List recent Hydra submission attempts (newest last) |
| GET | `/cardano/submissions/{event_id}` | Look up a single submission by event id |

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

**Education:** open **`/wine-journey.html`** (same dev server) for a companion page on the real wine-production path, aligned with the simulated ledger stages, teaching prompts, and offline-friendly illustrations under `frontend/public/education/`.

**Tests**

```bash
python -m pytest
```

## Configuration

- **Chain file**: Default path is `data/chain.json`. Override with environment variable `WINLEDGER_CHAIN_PATH` (absolute path to a `.json` file). Tests set this automatically to a temp file so they do not touch your dev chain.
- **Geo API keys**: For future OSM or vendor routing APIs, use environment variables or your campus secret store; do not commit secrets.
- **Geo cache path**: `GeoEnrichmentService` uses `SqliteGeoCache` at `data/geo_cache.sqlite` (created automatically).
- **Cardano / Hydra bridge** (off by default):
  - `WINELEDGER_HYDRA_MODE` — `disabled` (default), `dryrun`, or `live`.
  - `WINELEDGER_HYDRA_URL` — Hydra node base URL when `live`.
  - `WINELEDGER_HYDRA_HEAD_ID` — label stored on each submission for traceability.
  - `WINELEDGER_CARDANO_TX_BUILDER_URL` — sidecar (Lucid/Mesh/cardano-cli) implementing `POST /build`.
  - `WINELEDGER_CARDANO_NETWORK` — `preview` (default), `preprod`, or `mainnet`.
  - `WINELEDGER_CARDANO_REF_TOKEN` — CIP-68 reference asset name; defaults to `WINELEDGER-BATCH`.
  - `WINELEDGER_CARDANO_SUBMISSIONS_PATH` — dual-write log; defaults to `data/cardano_submissions.json`.

## License

See project policy for your institution or add a license file when you publish.
