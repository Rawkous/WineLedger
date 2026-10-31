# Supply chain simulator 
import uuid
import random
from datetime import datetime, timedelta, timezone
from typing import List
from .models import SupplyChainEvent

EVENT_SEQUENCE = [
    "HARVEST",
    "FERMENTATION",
    "BARREL_AGING",
    "BOTTLING",
    "TRANSPORT",
    "RETAIL",
]

BASE_LOCATION = {"lat": 38.2975, "lon": -122.2869}  # Napa-ish

def simulate_supply_chain(start_time: datetime | None = None) -> List[SupplyChainEvent]:
    if start_time is None:
        start_time = datetime.now(timezone.utc)

    events: List[SupplyChainEvent] = []
    current_time = start_time

    for event_type in EVENT_SEQUENCE:
        event_id = str(uuid.uuid4())
        # simple time progression
        delta_hours = random.randint(4, 72)
        current_time += timedelta(hours=delta_hours)

        location = {
            "lat": BASE_LOCATION["lat"] + random.uniform(-0.1, 0.1),
            "lon": BASE_LOCATION["lon"] + random.uniform(-0.1, 0.1),
        }

        metadata = {
            "temperature": round(random.uniform(8.0, 22.0), 1),
            "batch_id": "BATCH-2026-001",
            "notes": f"{event_type} event",
        }

        event = SupplyChainEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=current_time,
            location=location,
            metadata=metadata,
        )
        events.append(event)

    return events
