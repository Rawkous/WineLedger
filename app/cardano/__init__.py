"""Cardano + Hydra integration for WineLedger.

This package is intentionally **opt-in**. With no environment configuration
the bridge runs in `disabled` mode and the rest of the application behaves
exactly as before. Two other modes are available:

- ``dryrun`` — builds a CIP-68-shaped event datum and a deterministic
  fake transaction id locally; useful for tests, demos, and classroom
  walkthroughs without a real Cardano stack.
- ``live`` — forwards the built transaction to a configured tx-builder
  sidecar and submits it to a Hydra head over the Hydra node API.

The Python backend never builds raw Cardano transactions itself: that is
delegated to a sidecar (Lucid/Mesh/cardano-cli) reachable over HTTP.
"""

from .bridge import HydraBridge, HydraSubmission, SubmissionStatus
from .config import CardanoSettings, HydraMode, load_cardano_settings
from .datum import EventDatum, build_event_datum, validate_transition
from .hydra_client import HydraClient, HydraClientError, MockHydraClient
from .submissions import SubmissionRecord, SubmissionStore
from .tx_builder import (
    BuiltTransaction,
    DryRunTxBuilder,
    SidecarTxBuilder,
    TxBuilder,
    TxBuilderError,
)

__all__ = [
    "BuiltTransaction",
    "CardanoSettings",
    "DryRunTxBuilder",
    "EventDatum",
    "HydraBridge",
    "HydraClient",
    "HydraClientError",
    "HydraMode",
    "HydraSubmission",
    "MockHydraClient",
    "SidecarTxBuilder",
    "SubmissionRecord",
    "SubmissionStatus",
    "SubmissionStore",
    "TxBuilder",
    "TxBuilderError",
    "build_event_datum",
    "load_cardano_settings",
    "validate_transition",
]
