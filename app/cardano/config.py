"""Settings for the Cardano + Hydra integration.

All settings come from environment variables so the same code path can be
exercised on a laptop (``dryrun``) and against a real Hydra cluster
(``live``) without code changes. Defaults keep the integration off.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class HydraMode(str, Enum):
    DISABLED = "disabled"
    DRYRUN = "dryrun"
    LIVE = "live"


class CardanoNetwork(str, Enum):
    PREVIEW = "preview"
    PREPROD = "preprod"
    MAINNET = "mainnet"


_ENV_MODE = "WINELEDGER_HYDRA_MODE"
_ENV_HYDRA_URL = "WINELEDGER_HYDRA_URL"
_ENV_HYDRA_HEAD_ID = "WINELEDGER_HYDRA_HEAD_ID"
_ENV_TX_BUILDER_URL = "WINELEDGER_CARDANO_TX_BUILDER_URL"
_ENV_NETWORK = "WINELEDGER_CARDANO_NETWORK"
_ENV_REF_TOKEN = "WINELEDGER_CARDANO_REF_TOKEN"
_ENV_SUBMISSIONS_PATH = "WINELEDGER_CARDANO_SUBMISSIONS_PATH"
_ENV_HTTP_TIMEOUT = "WINELEDGER_CARDANO_HTTP_TIMEOUT_S"


@dataclass(frozen=True)
class CardanoSettings:
    """Resolved configuration consumed by :class:`HydraBridge`."""

    mode: HydraMode = HydraMode.DISABLED
    network: CardanoNetwork = CardanoNetwork.PREVIEW
    hydra_url: Optional[str] = None
    hydra_head_id: Optional[str] = None
    tx_builder_url: Optional[str] = None
    ref_token: str = "WINELEDGER-BATCH"
    submissions_path: Optional[Path] = None
    http_timeout_s: float = 5.0

    @property
    def enabled(self) -> bool:
        return self.mode is not HydraMode.DISABLED

    @property
    def requires_network(self) -> bool:
        return self.mode is HydraMode.LIVE


def _parse_mode(raw: Optional[str]) -> HydraMode:
    if not raw:
        return HydraMode.DISABLED
    try:
        return HydraMode(raw.strip().lower())
    except ValueError as exc:
        raise ValueError(
            f"Unknown {_ENV_MODE}={raw!r}; expected one of "
            f"{[m.value for m in HydraMode]}"
        ) from exc


def _parse_network(raw: Optional[str]) -> CardanoNetwork:
    if not raw:
        return CardanoNetwork.PREVIEW
    try:
        return CardanoNetwork(raw.strip().lower())
    except ValueError as exc:
        raise ValueError(
            f"Unknown {_ENV_NETWORK}={raw!r}; expected one of "
            f"{[n.value for n in CardanoNetwork]}"
        ) from exc


def load_cardano_settings(
    *,
    default_submissions_path: Optional[Path] = None,
    env: Optional[dict] = None,
) -> CardanoSettings:
    """Build :class:`CardanoSettings` from environment variables.

    A small wrapper so tests can pass an explicit ``env`` dict.
    """

    src = env if env is not None else os.environ

    mode = _parse_mode(src.get(_ENV_MODE))
    network = _parse_network(src.get(_ENV_NETWORK))

    submissions_raw = src.get(_ENV_SUBMISSIONS_PATH)
    submissions_path = (
        Path(submissions_raw).expanduser() if submissions_raw else default_submissions_path
    )

    timeout_raw = src.get(_ENV_HTTP_TIMEOUT)
    try:
        http_timeout_s = float(timeout_raw) if timeout_raw else 5.0
    except ValueError:
        http_timeout_s = 5.0

    return CardanoSettings(
        mode=mode,
        network=network,
        hydra_url=src.get(_ENV_HYDRA_URL) or None,
        hydra_head_id=src.get(_ENV_HYDRA_HEAD_ID) or None,
        tx_builder_url=src.get(_ENV_TX_BUILDER_URL) or None,
        ref_token=src.get(_ENV_REF_TOKEN) or "WINELEDGER-BATCH",
        submissions_path=submissions_path,
        http_timeout_s=http_timeout_s,
    )
