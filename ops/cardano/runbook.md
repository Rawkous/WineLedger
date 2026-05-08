# Cardano + Hydra runbook

Operational notes for running the bridge in `dryrun` (laptop / classroom)
and `live` (real Hydra head) modes. Treat this as the on-call companion
to [`doc/cardano-hydra.md`](../../doc/cardano-hydra.md), not a substitute
for the upstream Cardano and Hydra docs.

## Modes at a glance

| Mode | What it does | What it needs |
|------|--------------|---------------|
| `disabled` (default) | No Cardano work. Bridge calls return `None`. | Nothing. |
| `dryrun` | Builds the CIP-68 datum and a deterministic fake `tx_id`. Records to `data/cardano_submissions.json`. | Nothing. |
| `live` | Calls the configured tx-builder sidecar and submits the resulting CBOR to a Hydra node. | `cardano-node`, `hydra-node`, signing keys, sidecar service. |

Switch modes with `WINELEDGER_HYDRA_MODE=disabled|dryrun|live`.

## Quick health checks

```bash
curl -s http://127.0.0.1:8000/cardano/status | jq
curl -s http://127.0.0.1:8000/cardano/submissions | jq '.count'
curl -s http://127.0.0.1:8000/cardano/submissions/<event_id> | jq
curl -s -X POST http://127.0.0.1:8000/cardano/dryrun | jq '.datum'
```

## Failure modes

| Symptom | Where to look | Notes |
|---------|---------------|-------|
| `status.hydra.reachable == false` | Hydra node logs, network reachability of `WINELEDGER_HYDRA_URL`. | Bridge keeps recording `failed` submissions; local chain unaffected. |
| Submissions stuck in `failed` with `tx_builder:` errors | Tx-builder sidecar logs, request shape vs `SidecarTxBuilder` contract. | Validate the sidecar accepts `POST /build` with the documented payload. |
| Submissions stuck in `failed` with `hydra:` errors | Hydra node API version, head state (`Open` vs `Closed`). | Some Hydra versions require `NewTx` over WebSocket; swap `HttpHydraClient` for a custom client implementing the same Protocol. |
| `skipped` with "cannot follow" | Local chain order. | Stage transitions are enforced; reset chain or replay events in order. |
| Restart loses submissions | `WINELEDGER_CARDANO_SUBMISSIONS_PATH`. | Defaults to `data/cardano_submissions.json`; mount this volume in containers. |
| Head closes unexpectedly | Hydra logs, L1 confirmations. | After close, all `live` submissions fail. Re-open a head, point `WINELEDGER_HYDRA_HEAD_ID` at it, restart the app. |

## Cost model

The bridge itself is free; the Cardano stack underneath is not.

* L1 (per head, not per event): `Init`, `Commit` (per party), `Close`, contestation wait, and `Fanout`. These are normal Cardano txs and pay min fees. Budget for a handful of L1 txs per head lifecycle.
* L2 (Hydra body): transactions inside the head do not pay L1 fees, but participants still need UTxO inside the head equal to whatever value moves.
* Sidecar / RPC: if you use a hosted provider for sync (Blockfrost, Maestro, Demeter), factor request cost; if you run your own `cardano-node`, factor disk + bandwidth.
* Operations: running `cardano-node` + `hydra-node` reliably is the dominant recurring cost. Plan for monitoring, key custody, and on-call rotations before mainnet.

## Routine drills (testnet)

1. Open a head with two parties (operator + auditor demo).
2. Run `/simulate-once` with `WINELEDGER_HYDRA_MODE=live`; confirm `/cardano/submissions` shows `submitted` for the six events.
3. Inspect the Hydra head state to confirm the txs landed.
4. Close + fanout the head; confirm L1 reflects the final UTxO state.
5. Re-open a fresh head and re-run; confirm the submission store keeps history across heads.

## Phase 1 helper: native-script NFT minting (Mesh)

If you want a **standalone L1 sanity check** (no Hydra, no sidecar) using
Mesh and native scripts, use:

- `ops/cardano/nft-collection/README.md`

This tool mints multiple CIP-25 NFTs in a single tx under a time-locked
native policy (signature + `before` slot).

## Key custody reminders

* Never commit `*.sk` files. Keep them out of compose volumes that reach git.
* Treat the tx-builder sidecar as a signer: it owns spending keys and should run with restricted egress. The Python backend deliberately does not hold signing material.
* For mainnet, separate operator keys from policy keys; rotate when staff changes.
