import pytest
from fastapi.testclient import TestClient

from app.blockchain import Blockchain
from app.main import app


@pytest.fixture
def client():
    app.state.blockchain = Blockchain()
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_simulate_once_returns_blocks(client):
    r = client.get("/simulate-once")
    assert r.status_code == 200
    data = r.json()
    assert data["valid_chain"] is True
    assert len(data["blocks"]) == 6
    assert "visual" in data["blocks"][0]
    assert "hue" in data["blocks"][0]["visual"]
