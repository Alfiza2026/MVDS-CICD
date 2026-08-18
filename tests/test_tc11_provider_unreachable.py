"""TC11 - Consumer handles provider being unreachable gracefully."""

from unittest.mock import patch
import requests


def test_discover_when_provider_down(consumer_client):
    """Consumer should return 503 when provider is unreachable during discovery."""
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        response = consumer_client.get("/discover")

    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "error"
    assert "provider unreachable" in data["reason"]


def test_negotiate_when_provider_down(consumer_client):
    """Consumer should return 503 when provider is unreachable during negotiation."""
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        response = consumer_client.post(
            "/negotiate",
            json={"assetId": "asset-001"},
        )

    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "error"
    assert "provider unreachable" in data["reason"]


def test_transfer_when_provider_down(consumer_client):
    """Consumer should return 503 when provider is unreachable during transfer."""
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection refused")):
        response = consumer_client.post(
            "/transfer",
            json={"contractId": "contract-001"},
        )

    assert response.status_code == 503
    data = response.get_json()
    assert data["status"] == "error"
    assert "provider unreachable" in data["reason"]
