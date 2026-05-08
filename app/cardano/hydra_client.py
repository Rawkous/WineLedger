"""Thin async client for the Cardano Hydra node API.

We only need three things from a running Hydra head:

1. A liveness / status check so the bridge can surface what is going on.
2. A way to submit a freshly built transaction.
3. A way to inspect head state when investigating a failure.

The real Hydra node API talks WebSockets for streaming head events plus
HTTP for snapshots and transaction submission (``POST /commit``,
``POST /cardano-transaction`` depending on version). The interface
captured here is deliberately minimal so it can wrap whichever route the
deployed Hydra version exposes.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

import httpx


class HydraClientError(RuntimeError):
    """Network or protocol error talking to the Hydra node."""


@dataclass(frozen=True)
class HydraStatus:
    reachable: bool
    head_id: Optional[str]
    state: Optional[str]
    detail: Optional[str] = None

    def to_json(self) -> Dict[str, Any]:
        return {
            "reachable": self.reachable,
            "head_id": self.head_id,
            "state": self.state,
            "detail": self.detail,
        }


class HydraClient(Protocol):
    """Subset of the Hydra node API the bridge needs."""

    async def status(self) -> HydraStatus:  # pragma: no cover
        ...

    async def submit_tx(self, cbor_hex: str) -> str:  # pragma: no cover
        ...


class HttpHydraClient:
    """HTTP client speaking to a Hydra node over its REST surface.

    The Hydra HTTP routes have evolved across releases. We keep this
    client narrow and forgiving:

    * ``status()`` calls ``GET /head`` first, then falls back to
      ``GET /protocol-parameters`` to detect liveness on older builds.
    * ``submit_tx()`` posts CBOR-hex to ``POST /cardano-transaction``;
      operators that route submission through a WebSocket ``NewTx``
      command can plug a different client by depending on the
      :class:`HydraClient` Protocol instead.
    """

    def __init__(
        self,
        *,
        base_url: str,
        timeout_s: float = 5.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_s = timeout_s
        self._client = client

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        url = f"{self._base_url}{path}"
        if self._client is not None:
            return await self._client.request(
                method, url, json=json_body, timeout=self._timeout_s
            )
        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            return await client.request(method, url, json=json_body)

    async def status(self) -> HydraStatus:
        try:
            response = await self._request("GET", "/head")
        except httpx.HTTPError as exc:
            return HydraStatus(reachable=False, head_id=None, state=None, detail=str(exc))

        if response.status_code == 404:
            try:
                fallback = await self._request("GET", "/protocol-parameters")
            except httpx.HTTPError as exc:
                return HydraStatus(reachable=False, head_id=None, state=None, detail=str(exc))
            reachable = fallback.status_code < 400
            return HydraStatus(
                reachable=reachable,
                head_id=None,
                state="unknown",
                detail=None if reachable else fallback.text[:200],
            )

        if response.status_code >= 400:
            return HydraStatus(
                reachable=False,
                head_id=None,
                state=None,
                detail=response.text[:200],
            )

        try:
            data = response.json()
        except json.JSONDecodeError:
            return HydraStatus(reachable=True, head_id=None, state="unknown")

        return HydraStatus(
            reachable=True,
            head_id=str(data.get("headId") or data.get("head_id") or "") or None,
            state=str(data.get("state") or data.get("tag") or "") or None,
        )

    async def submit_tx(self, cbor_hex: str) -> str:
        if not cbor_hex:
            raise HydraClientError("Refusing to submit an empty cbor_hex")
        try:
            response = await self._request(
                "POST",
                "/cardano-transaction",
                json_body={"cborHex": cbor_hex, "type": "Tx ConwayEra", "description": ""},
            )
        except httpx.HTTPError as exc:
            raise HydraClientError(f"Hydra submit failed: {exc}") from exc

        if response.status_code >= 400:
            raise HydraClientError(
                f"Hydra submit returned {response.status_code}: {response.text[:200]}"
            )
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise HydraClientError("Hydra submit response was not JSON") from exc
        tx_id = str(data.get("txId") or data.get("tx_id") or "").strip()
        if not tx_id:
            raise HydraClientError(f"Hydra submit response missing txId: {data!r}")
        return tx_id


class MockHydraClient:
    """In-memory client used by tests and ``dryrun`` mode.

    Records every submission so tests can assert on the call sequence
    without a network. ``head_id`` and ``state`` can be set by tests to
    simulate different head conditions.
    """

    def __init__(
        self,
        *,
        head_id: str = "mock-head",
        state: str = "Open",
        reachable: bool = True,
    ) -> None:
        self.head_id = head_id
        self.state = state
        self.reachable = reachable
        self.submissions: list[str] = []

    async def status(self) -> HydraStatus:
        return HydraStatus(
            reachable=self.reachable,
            head_id=self.head_id if self.reachable else None,
            state=self.state if self.reachable else None,
        )

    async def submit_tx(self, cbor_hex: str) -> str:
        if not self.reachable:
            raise HydraClientError("Mock Hydra is unreachable")
        self.submissions.append(cbor_hex)
        return f"mock-tx-{len(self.submissions):04d}"
