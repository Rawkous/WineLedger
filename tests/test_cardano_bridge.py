import asyncio
from datetime import datetime, timezone

import pytest

from app.blockchain import Blockchain
from app.cardano import (
    HydraBridge,
    HydraMode,
    MockHydraClient,
    SubmissionStatus,
    SubmissionStore,
)
from app.cardano.config import CardanoSettings
from app.cardano.tx_builder import DryRunTxBuilder
from app.models import SupplyChainEvent


def _settings(mode: HydraMode, *, submissions_path=None) -> CardanoSettings:
    return CardanoSettings(
        mode=mode,
        ref_token="LOT-1",
        submissions_path=submissions_path,
    )


def _event(event_type: str, *, event_id: str) -> SupplyChainEvent:
    return SupplyChainEvent(
        event_id=event_id,
        event_type=event_type,
        timestamp=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        location={"lat": 38.3, "lon": -122.3},
        metadata={"temperature": 12.0},
    )


def _bridge(mode: HydraMode, *, submissions_path=None):
    settings = _settings(mode, submissions_path=submissions_path)
    return HydraBridge(
        settings=settings,
        tx_builder=DryRunTxBuilder(),
        client=MockHydraClient(),
        store=SubmissionStore(submissions_path),
    )


def test_disabled_mode_returns_none():
    bc = Blockchain()
    bc.add_block(_event("HARVEST", event_id="e1"))
    bridge = _bridge(HydraMode.DISABLED)

    submission = asyncio.run(
        bridge.submit_block(bc.chain[-1], prev_event_type="GENESIS")
    )
    assert submission is None
    assert len(bridge.store) == 0


def test_dryrun_records_submission_with_deterministic_tx_id():
    bc = Blockchain()
    bc.add_block(_event("HARVEST", event_id="e1"))
    bridge = _bridge(HydraMode.DRYRUN)
    block = bc.chain[-1]

    submission = asyncio.run(
        bridge.submit_block(block, prev_event_type="GENESIS")
    )
    assert submission is not None
    assert submission.status is SubmissionStatus.DRY_RUN
    assert submission.tx_id  # deterministic SHA-256 hex
    assert len(submission.tx_id) == 64

    again = asyncio.run(
        _bridge(HydraMode.DRYRUN).submit_block(block, prev_event_type="GENESIS")
    )
    assert again is not None
    assert again.tx_id == submission.tx_id


def test_dryrun_skips_invalid_transition_without_raising():
    bc = Blockchain()
    bc.add_block(_event("BOTTLING", event_id="bad"))
    bridge = _bridge(HydraMode.DRYRUN)

    submission = asyncio.run(
        bridge.submit_block(bc.chain[-1], prev_event_type="HARVEST")
    )
    assert submission is not None
    assert submission.status is SubmissionStatus.SKIPPED
    assert "cannot follow" in (submission.error or "")


def test_live_mode_uses_mock_hydra_client():
    bc = Blockchain()
    bc.add_block(_event("HARVEST", event_id="e1"))
    settings = CardanoSettings(mode=HydraMode.LIVE, ref_token="LOT-1")
    mock_client = MockHydraClient(head_id="head-7")
    bridge = HydraBridge(
        settings=settings,
        tx_builder=DryRunTxBuilder(),
        client=mock_client,
        store=SubmissionStore(None),
    )

    submission = asyncio.run(
        bridge.submit_block(bc.chain[-1], prev_event_type="GENESIS")
    )
    assert submission is not None
    assert submission.status is SubmissionStatus.SUBMITTED
    assert submission.tx_id.startswith("mock-tx-")
    assert mock_client.submissions == [""]  # DryRunTxBuilder produces empty cbor


def test_submission_store_persists_to_disk(tmp_path):
    submissions_path = tmp_path / "submissions.json"
    bc = Blockchain()
    bc.add_block(_event("HARVEST", event_id="e1"))

    bridge = _bridge(HydraMode.DRYRUN, submissions_path=submissions_path)
    submission = asyncio.run(
        bridge.submit_block(bc.chain[-1], prev_event_type="GENESIS")
    )
    assert submission is not None

    reopened = SubmissionStore(submissions_path)
    record = reopened.get(submission.event_id)
    assert record is not None
    assert record.tx_id == submission.tx_id
    assert record.status == "dry_run"


def test_status_payload_contains_mode_and_counts():
    bridge = _bridge(HydraMode.DRYRUN)
    payload = asyncio.run(bridge.status())
    assert payload["mode"] == "dryrun"
    assert payload["submissions"] == 0
    assert payload["tx_builder"] == "dryrun"
