# Geo enrichment: primary static provider + pluggable cache (SQLite local; NDR swap same interface)

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from .models import SupplyChainEvent


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


# Rough CA wine-country buckets for demo (not authoritative appellations)
def _region_code(lat: float, lon: float) -> str:
    if 38.2 <= lat <= 38.6 and -122.6 <= lon <= -122.2:
        return "US-CA-NAPA"
    if 38.3 <= lat <= 38.7 and -123.0 <= lon <= -122.4:
        return "US-CA-SONOMA"
    if 34.0 <= lat <= 42.0 and -124.5 <= lon <= -114.0:
        return "US-CA-OTHER"
    return "US-UNKNOWN"


class GeoCacheBackend(Protocol):
    """Implementations: local SQLite (default), or sync object store / NDR bucket via same get/set."""

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        ...

    def set(self, key: str, value: Dict[str, Any]) -> None:
        ...


class SqliteGeoCache:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS geo_cache (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                )
                """
            )
            conn.commit()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self._path) as conn:
            row = conn.execute("SELECT payload FROM geo_cache WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def set(self, key: str, value: Dict[str, Any]) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO geo_cache (key, payload) VALUES (?, ?)",
                (key, json.dumps(value, sort_keys=True)),
            )
            conn.commit()


class GeoEnrichmentService:
    """
    Adapter: one primary provider (static haversine + region bucketing).
    Normalized keys land in event.metadata; large geometries stay as geometry_ref only.
    """

    def __init__(
        self,
        cache: Optional[GeoCacheBackend] = None,
        *,
        provider: str = "static_haversine",
    ) -> None:
        self._cache = cache
        self._provider = provider

    def _cache_key(self, lat: float, lon: float, prev: Optional[Dict[str, float]]) -> str:
        parts = f"{round(lat, 5)}:{round(lon, 5)}"
        if prev:
            parts += f":{round(prev['lat'], 5)}:{round(prev['lon'], 5)}"
        return hashlib.sha256(parts.encode("utf-8")).hexdigest()

    def enrich(
        self,
        event: SupplyChainEvent,
        previous_location: Optional[Dict[str, float]] = None,
    ) -> SupplyChainEvent:
        lat, lon = event.location["lat"], event.location["lon"]
        key = self._cache_key(lat, lon, previous_location)

        if self._cache:
            cached = self._cache.get(key)
            if cached is not None:
                merged = {**event.metadata, **cached, "geo_cache_hit": True, "geo_provider": self._provider}
                return SupplyChainEvent(
                    event_id=event.event_id,
                    event_type=event.event_type,
                    timestamp=event.timestamp,
                    location=dict(event.location),
                    metadata=merged,
                )

        route_km: Optional[float] = None
        if previous_location:
            route_km = round(
                _haversine_km(
                    previous_location["lat"],
                    previous_location["lon"],
                    lat,
                    lon,
                ),
                3,
            )

        region = _region_code(lat, lon)
        geom_hash = hashlib.sha256(f"{lat:.5f},{lon:.5f}".encode()).hexdigest()[:16]
        geometry_ref = f"ndr://geo/points/{geom_hash}"

        extra: Dict[str, Any] = {
            "route_km": route_km,
            "region_code": region,
            "geometry_ref": geometry_ref,
            "geo_cache_hit": False,
            "geo_provider": self._provider,
        }

        if self._cache:
            to_store = {k: v for k, v in extra.items() if k not in ("geo_cache_hit",)}
            self._cache.set(key, to_store)

        merged_meta = {**event.metadata, **extra}
        return SupplyChainEvent(
            event_id=event.event_id,
            event_type=event.event_type,
            timestamp=event.timestamp,
            location=dict(event.location),
            metadata=merged_meta,
        )
