"""Persistent record of Hydra submissions, keyed by event id.

Acts as the dual-write surface called out in the roadmap: the canonical
local chain stays in ``data/chain.json`` while every Hydra submission
attempt is written here so we can correlate ``event_id`` ↔ ``tx_id``
across restarts. The store is intentionally simple JSON so it is easy to
inspect from the browser, ``jq``, or a notebook.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class SubmissionRecord:
    event_id: str
    block_index: int
    block_hash: str
    tx_id: str
    status: str
    mode: str
    head_id: Optional[str] = None
    submitted_at: Optional[str] = None
    confirmed_at: Optional[str] = None
    error: Optional[str] = None
    datum: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_json(self) -> Dict[str, Any]:
        return asdict(self)


class SubmissionStore:
    """Tiny JSON-backed key-value store over :class:`SubmissionRecord`.

    All public methods are thread-safe. The store keeps the full set in
    memory and rewrites the file on every change; volume here is bounded
    by the number of supply-chain events so this is cheap.
    """

    _SCHEMA_VERSION = 1

    def __init__(self, path: Optional[Path]) -> None:
        self._path = path
        self._lock = RLock()
        self._records: Dict[str, SubmissionRecord] = {}
        if path is not None:
            self._load()

    def _load(self) -> None:
        if self._path is None or not self._path.exists():
            return
        raw = self._path.read_text(encoding="utf-8").strip()
        if not raw:
            return
        data = json.loads(raw)
        for entry in data.get("submissions", []):
            record = SubmissionRecord(**entry)
            self._records[record.event_id] = record

    def _persist(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self._SCHEMA_VERSION,
            "submissions": [r.to_json() for r in self._records.values()],
        }
        text = json.dumps(payload, indent=2, sort_keys=False)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(self._path)

    def upsert(self, record: SubmissionRecord) -> SubmissionRecord:
        with self._lock:
            self._records[record.event_id] = record
            self._persist()
            return record

    def get(self, event_id: str) -> Optional[SubmissionRecord]:
        with self._lock:
            return self._records.get(event_id)

    def list(self, *, limit: Optional[int] = None) -> List[SubmissionRecord]:
        with self._lock:
            items: Iterable[SubmissionRecord] = self._records.values()
            ordered = sorted(items, key=lambda r: r.block_index)
            if limit is not None:
                ordered = ordered[-limit:]
            return list(ordered)

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)
