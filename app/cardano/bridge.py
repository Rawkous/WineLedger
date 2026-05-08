"""High-level orchestrator that ties datum + builder + Hydra together.

The bridge is the only thing the FastAPI layer talks to. It accepts a
:class:`~app.models.Block` (and its preceding event type), decides
whether it should attempt a Hydra submission, and returns a
:class:`HydraSubmission` describing what happened. Failures never raise
back into the request path — the local chain is the source of truth and
Cardano integration is best-effort by design.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from ..models import Block
from .config import CardanoSettings, HydraMode
from .datum import (
    GENESIS_EVENT_TYPE,
    EventDatum,
    TransitionError,
    build_event_datum,
    validate_transition,
)
from .hydra_client import HydraClient, HydraClientError, HydraStatus, MockHydraClient
from .submissions import SubmissionRecord, SubmissionStore
from .tx_builder import (
    BuiltTransaction,
    DryRunTxBuilder,
    TxBuilder,
    TxBuilderError,
)


_LOG = logging.getLogger("wineledger.cardano")


class SubmissionStatus(str, Enum):
    SKIPPED = "skipped"
    DRY_RUN = "dry_run"
    SUBMITTED = "submitted"
    FAILED = "failed"


@dataclass
class HydraSubmission:
    event_id: str
    block_index: int
    block_hash: str
    tx_id: str
    status: SubmissionStatus
    mode: HydraMode
    head_id: Optional[str] = None
    error: Optional[str] = None
    datum: Optional[EventDatum] = None
    submitted_at: Optional[str] = None

    def to_payload(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "block_index": self.block_index,
            "block_hash": self.block_hash,
            "tx_id": self.tx_id,
            "status": self.status.value,
            "mode": self.mode.value,
            "head_id": self.head_id,
            "error": self.error,
            "submitted_at": self.submitted_at,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class HydraBridge:
    """Submits WineLedger blocks to a Cardano Hydra head when configured.

    The bridge keeps three pluggable seams so it can be exercised with or
    without a real Cardano stack:

    * :class:`~app.cardano.tx_builder.TxBuilder` — builds the tx body.
    * :class:`~app.cardano.hydra_client.HydraClient` — talks to Hydra.
    * :class:`~app.cardano.submissions.SubmissionStore` — dual-write log.
    """

    def __init__(
        self,
        *,
        settings: CardanoSettings,
        tx_builder: TxBuilder,
        client: HydraClient,
        store: SubmissionStore,
    ) -> None:
        self._settings = settings
        self._builder = tx_builder
        self._client = client
        self._store = store

    @property
    def settings(self) -> CardanoSettings:
        return self._settings

    @property
    def store(self) -> SubmissionStore:
        return self._store

    async def status(self) -> Dict[str, Any]:
        """Lightweight diagnostic for ``GET /cardano/status``."""

        info: Dict[str, Any] = {
            "mode": self._settings.mode.value,
            "network": self._settings.network.value,
            "ref_token": self._settings.ref_token,
            "hydra_url": self._settings.hydra_url,
            "hydra_head_id": self._settings.hydra_head_id,
            "tx_builder": getattr(self._builder, "name", type(self._builder).__name__),
            "submissions": len(self._store),
        }
        if self._settings.requires_network:
            try:
                hydra_status: HydraStatus = await self._client.status()
            except Exception as exc:  # pragma: no cover - defensive
                info["hydra"] = {
                    "reachable": False,
                    "detail": f"{type(exc).__name__}: {exc}",
                }
            else:
                info["hydra"] = hydra_status.to_json()
        else:
            info["hydra"] = None
        return info

    async def preview(self, block: Block) -> EventDatum:
        """Build the datum for a block without submitting anything."""

        return build_event_datum(block, ref_token=self._settings.ref_token)

    async def submit_block(
        self,
        block: Block,
        *,
        prev_event_type: Optional[str],
    ) -> Optional[HydraSubmission]:
        """Best-effort Hydra submission for ``block``.

        ``None`` is returned when the bridge is disabled or the block is
        the genesis row (which has no business value on Cardano). All
        failure modes are caught and recorded; never raises.
        """

        if not self._settings.enabled:
            return None

        if block.event.event_type == GENESIS_EVENT_TYPE:
            return None

        try:
            validate_transition(prev_event_type, block.event.event_type)
        except TransitionError as exc:
            _LOG.warning("Hydra bridge skipping block %s: %s", block.index, exc)
            submission = HydraSubmission(
                event_id=block.event.event_id,
                block_index=block.index,
                block_hash=block.hash,
                tx_id="",
                status=SubmissionStatus.SKIPPED,
                mode=self._settings.mode,
                head_id=self._settings.hydra_head_id,
                error=str(exc),
                submitted_at=_now_iso(),
            )
            self._record(submission, datum=None)
            return submission

        datum = build_event_datum(block, ref_token=self._settings.ref_token)

        try:
            built = await self._builder.build(datum)
        except TxBuilderError as exc:
            return self._fail(
                block,
                datum=datum,
                tx_id="",
                error=f"tx_builder: {exc}",
            )
        except Exception as exc:  # pragma: no cover - defensive
            return self._fail(
                block,
                datum=datum,
                tx_id="",
                error=f"tx_builder unexpected: {type(exc).__name__}: {exc}",
            )

        if self._settings.mode is HydraMode.DRYRUN:
            submission = HydraSubmission(
                event_id=block.event.event_id,
                block_index=block.index,
                block_hash=block.hash,
                tx_id=built.tx_id,
                status=SubmissionStatus.DRY_RUN,
                mode=self._settings.mode,
                head_id=self._settings.hydra_head_id,
                datum=built.datum,
                submitted_at=_now_iso(),
            )
            self._record(submission, datum=built.datum)
            return submission

        return await self._submit_live(block, built)

    async def _submit_live(
        self,
        block: Block,
        built: BuiltTransaction,
    ) -> HydraSubmission:
        try:
            tx_id = await self._client.submit_tx(built.cbor_hex)
        except HydraClientError as exc:
            return self._fail(
                block,
                datum=built.datum,
                tx_id=built.tx_id,
                error=f"hydra: {exc}",
            )
        except Exception as exc:  # pragma: no cover - defensive
            return self._fail(
                block,
                datum=built.datum,
                tx_id=built.tx_id,
                error=f"hydra unexpected: {type(exc).__name__}: {exc}",
            )

        submission = HydraSubmission(
            event_id=block.event.event_id,
            block_index=block.index,
            block_hash=block.hash,
            tx_id=tx_id or built.tx_id,
            status=SubmissionStatus.SUBMITTED,
            mode=self._settings.mode,
            head_id=self._settings.hydra_head_id,
            datum=built.datum,
            submitted_at=_now_iso(),
        )
        self._record(submission, datum=built.datum)
        return submission

    def _fail(
        self,
        block: Block,
        *,
        datum: Optional[EventDatum],
        tx_id: str,
        error: str,
    ) -> HydraSubmission:
        _LOG.warning(
            "Hydra bridge failure for block %s (%s): %s",
            block.index,
            block.event.event_type,
            error,
        )
        submission = HydraSubmission(
            event_id=block.event.event_id,
            block_index=block.index,
            block_hash=block.hash,
            tx_id=tx_id,
            status=SubmissionStatus.FAILED,
            mode=self._settings.mode,
            head_id=self._settings.hydra_head_id,
            error=error,
            datum=datum,
            submitted_at=_now_iso(),
        )
        self._record(submission, datum=datum)
        return submission

    def _record(self, submission: HydraSubmission, *, datum: Optional[EventDatum]) -> None:
        record = SubmissionRecord(
            event_id=submission.event_id,
            block_index=submission.block_index,
            block_hash=submission.block_hash,
            tx_id=submission.tx_id,
            status=submission.status.value,
            mode=submission.mode.value,
            head_id=submission.head_id,
            submitted_at=submission.submitted_at,
            error=submission.error,
            datum=datum.to_json() if datum is not None else {},
        )
        self._store.upsert(record)

    @classmethod
    def from_settings(
        cls,
        settings: CardanoSettings,
        *,
        tx_builder: Optional[TxBuilder] = None,
        client: Optional[HydraClient] = None,
        store: Optional[SubmissionStore] = None,
    ) -> "HydraBridge":
        """Build a bridge using sensible defaults for the requested mode.

        ``tx_builder``/``client`` overrides exist so tests can inject
        fakes without going through the environment.
        """

        if tx_builder is None:
            tx_builder = _default_tx_builder(settings)
        if client is None:
            client = _default_hydra_client(settings)
        if store is None:
            store = SubmissionStore(settings.submissions_path)
        return cls(
            settings=settings,
            tx_builder=tx_builder,
            client=client,
            store=store,
        )


def _default_tx_builder(settings: CardanoSettings) -> TxBuilder:
    if settings.mode is HydraMode.LIVE and settings.tx_builder_url:
        from .tx_builder import SidecarTxBuilder

        return SidecarTxBuilder(
            url=settings.tx_builder_url,
            network=settings.network.value,
            ref_token=settings.ref_token,
            timeout_s=settings.http_timeout_s,
        )
    return DryRunTxBuilder()


def _default_hydra_client(settings: CardanoSettings) -> HydraClient:
    if settings.mode is HydraMode.LIVE and settings.hydra_url:
        from .hydra_client import HttpHydraClient

        return HttpHydraClient(
            base_url=settings.hydra_url,
            timeout_s=settings.http_timeout_s,
        )
    return MockHydraClient(head_id=settings.hydra_head_id or "mock-head")
