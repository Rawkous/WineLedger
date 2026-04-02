# Event + location + metadata → visual parameters for the renderer

from __future__ import annotations

import math
from typing import Any, Dict

from .models import SupplyChainEvent
from .schemas import VisualParamsSchema

# Hue wheel positions by supply-chain stage (degrees)
_EVENT_HUE: Dict[str, float] = {
    "GENESIS": 0.0,
    "HARVEST": 95.0,
    "FERMENTATION": 45.0,
    "BARREL_AGING": 28.0,
    "BOTTLING": 200.0,
    "TRANSPORT": 265.0,
    "RETAIL": 320.0,
}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def event_to_visual_params(event: SupplyChainEvent) -> VisualParamsSchema:
    et = event.event_type
    base_hue = _EVENT_HUE.get(et, 180.0)
    meta: Dict[str, Any] = event.metadata

    temp = float(meta.get("temperature", 15.0))
    temp_t = _clamp01((temp - 8.0) / 14.0)

    route = meta.get("route_km")
    if route is None:
        motion = 0.35 + 0.25 * math.sin(event.timestamp.timestamp() / 3600.0)
    else:
        motion = _clamp01(min(1.0, float(route) / 50.0))

    burst = int(20 + 80 * temp_t + (20 if et == "HARVEST" else 0))
    if et == "TRANSPORT":
        burst += 40

    sat = 0.55 + 0.35 * temp_t
    bri = 0.45 + 0.4 * (1.0 - abs(temp_t - 0.5))

    return VisualParamsSchema(
        hue=base_hue + 5.0 * temp_t,
        saturation=_clamp01(sat),
        brightness=_clamp01(bri),
        motion=_clamp01(motion),
        particle_burst=min(500, burst),
        label=et.replace("_", " ").title(),
    )
