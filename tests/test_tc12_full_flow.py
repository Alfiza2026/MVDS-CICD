"""TC12 - End-to-end data flow through consumer orchestration."""

from unittest.mock import patch, MagicMock


def _mock_provider_responses(*args, **kwargs):
    """Simulate successful provider responses for the full flow."""
    url = args[0] if args else kwargs.get("url", "")
    mock_resp = MagicMock()

    if "/catalogue" in url:
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"assetId": "asset-001", "name": "Test Dataset", "description": "Sample data"}
        ]
    elif "/negotiate" in url:
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "agreed",
            "contractId": "contract-001",
            "policyId": "policy-001",
        }
    elif "/transfer" in url:
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "completed",
            "transferId": "transfer-001",
            "bytes": 2048,
        }
    return mock_resp


def test_full_flow_success(consumer_client):
    """Full flow should complete successfully when provider is healthy."""
    with patch("requests.get", side_effect=_mock_provider_responses):
        with patch("requests.post", side_effect=_mock_provider_responses):
            response = consumer_client.get("/run-full-flow")

    assert response.status_code == 200
    data = response.get_json()
    assert data["flow"] == "completed"
    assert data["success"] is True
    assert data["results"]["discovery"]["success"] is True
    assert data["results"]["negotiation"]["success"] is True
    assert data["results"]["transfer"]["success"] is True
    assert "duration_seconds" in data


def test_full_flow_fails_at_negotiation(consumer_client):
    """Flow should stop and report failure if negotiation fails."""

    def _fail_at_negotiate(*args, **kwargs):
        url = args[0] if args else kwargs.get("url", "")
        mock_resp = MagicMock()
        if "/negotiate" in url:
            mock_resp.status_code = 403
            mock_resp.json.return_value = {"status": "rejected", "reason": "policy mismatch"}
        elif "/transfer" in url:
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"status": "completed"}
        return mock_resp

    with patch("requests.get", side_effect=_mock_provider_responses):
        with patch("requests.post", side_effect=_fail_at_negotiate):
            response = consumer_client.get("/run-full-flow")

    assert response.status_code == 502
    data = response.get_json()
    assert data["flow"] == "partial"
    assert data["success"] is False
    assert data["results"]["negotiation"]["success"] is False
