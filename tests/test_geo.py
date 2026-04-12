from datetime import datetime

from app.geo_enrichment import GeoEnrichmentService
from app.models import SupplyChainEvent


def test_geo_enrich_adds_region_and_geometry_ref():
    geo = GeoEnrichmentService(cache=None)
    ev = SupplyChainEvent(
        event_id="1",
        event_type="HARVEST",
        timestamp=datetime.utcnow(),
        location={"lat": 38.4, "lon": -122.4},
        metadata={},
    )
    out = geo.enrich(ev, None)
    assert out.metadata.get("region_code")
    assert "geometry_ref" in out.metadata
    assert out.metadata.get("route_km") is None


def test_geo_enrich_route_with_previous():
    geo = GeoEnrichmentService(cache=None)
    ev = SupplyChainEvent(
        event_id="2",
        event_type="TRANSPORT",
        timestamp=datetime.utcnow(),
        location={"lat": 38.41, "lon": -122.41},
        metadata={},
    )
    prev = {"lat": 38.4, "lon": -122.4}
    out = geo.enrich(ev, prev)
    assert out.metadata.get("route_km") is not None
    assert out.metadata["route_km"] < 5.0
