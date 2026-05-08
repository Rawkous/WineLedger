"""Off-chain Cardano transaction builders.

The Python backend deliberately does not assemble raw Cardano
transactions itself: that work belongs to a sidecar (Lucid / Mesh /
``cardano-cli``) that owns signing keys and protocol parameters. This
module declares the :class:`TxBuilder` Protocol the rest of the code
depends on, plus two implementations:

* :class:`DryRunTxBuilder` — pure-Python, deterministic. Used by the
  ``dryrun`` mode and tests.
* :class:`SidecarTxBuilder` — POSTs the projected datum to a configured
  HTTP service that returns CBOR + a tx id. Activated by the ``live``
  mode.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

import httpx

from .datum import EventDatum


class TxBuilderError(RuntimeError):
    """Raised when a transaction cannot be built or signed."""


@dataclass(frozen=True)
class BuiltTransaction:
    """Result of building a transaction.

    ``cbor_hex`` is empty for :class:`DryRunTxBuilder`. ``tx_id`` is
    always set so it can be used as a stable correlation handle even in
    dry-run mode.
    """

    tx_id: str
    cbor_hex: str
    datum: EventDatum
    builder: str


class TxBuilder(Protocol):
    """Builds (and ideally signs) a Cardano transaction from a datum."""

    name: str

    async def build(self, datum: EventDatum) -> BuiltTransaction:  # pragma: no cover
        ...


class DryRunTxBuilder:
    """Deterministic builder used for tests, demos, and ``dryrun`` mode.

    Produces a stable ``tx_id`` derived from
    :meth:`EventDatum.content_hash` so the same event always yields the
    same fake transaction id. No network or filesystem access.
    """

    name = "dryrun"

    async def build(self, datum: EventDatum) -> BuiltTransaction:
        tx_id = datum.content_hash()
        return BuiltTransaction(
            tx_id=tx_id,
            cbor_hex="",
            datum=datum,
            builder=self.name,
        )


class SidecarTxBuilder:
    """Delegates tx assembly to a JSON HTTP sidecar.

    The sidecar contract is intentionally minimal so it can be a small
    Lucid script in Node, a Mesh service, or a wrapper around
    ``cardano-cli``:

    Request (``POST {url}/build``)::

        {"datum": <EventDatum.to_json()>, "ref_token": str, "network": str}

    Response::

        {"tx_id": "<hex>", "cbor_hex": "<hex>"}

    Anything else is treated as a build failure.
    """

    name = "sidecar"

    def __init__(
        self,
        *,
        url: str,
        network: str,
        ref_token: str,
        timeout_s: float = 5.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._network = network
        self._ref_token = ref_token
        self._timeout_s = timeout_s
        self._client = client

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._url}{path}"
        if self._client is not None:
            response = await self._client.post(url, json=payload, timeout=self._timeout_s)
        else:
            async with httpx.AsyncClient(timeout=self._timeout_s) as client:
                response = await client.post(url, json=payload)
        if response.status_code >= 400:
            raise TxBuilderError(
                f"Sidecar {url} returned {response.status_code}: {response.text[:200]}"
            )
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise TxBuilderError(f"Sidecar {url} returned non-JSON body") from exc

    async def build(self, datum: EventDatum) -> BuiltTransaction:
        body = {
            "datum": datum.to_json(),
            "ref_token": self._ref_token,
            "network": self._network,
        }
        data = await self._post("/build", body)
        tx_id = str(data.get("tx_id") or "").strip()
        cbor_hex = str(data.get("cbor_hex") or "").strip()
        if not tx_id or not cbor_hex:
            raise TxBuilderError(
                f"Sidecar response missing tx_id/cbor_hex: keys={list(data.keys())}"
            )
        return BuiltTransaction(
            tx_id=tx_id,
            cbor_hex=cbor_hex,
            datum=datum,
            builder=self.name,
        )
