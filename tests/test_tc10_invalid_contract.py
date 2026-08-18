"""TC10 - Transfer with an invalid contract ID is rejected."""


def test_transfer_invalid_contract_id(provider_client):
    """Provider should reject a transfer request with a non-existent contract."""
    response = provider_client.post(
        "/transfer",
        json={"contractId": "contract-999"},
        headers={"Authorization": "Bearer consumer-auth-token-2026"},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "rejected"
    assert "invalid contract" in data["reason"]


def test_transfer_missing_contract_id(provider_client):
    """Provider should reject a transfer request with no contract ID."""
    response = provider_client.post(
        "/transfer",
        json={},
        headers={"Authorization": "Bearer consumer-auth-token-2026"},
    )

    assert response.status_code == 400
    data = response.get_json()
    assert data["status"] == "rejected"
    assert "invalid contract" in data["reason"]


def test_negotiate_invalid_asset_id(provider_client):
    """Provider should return 404 when negotiating for a non-existent asset."""
    response = provider_client.post(
        "/negotiate",
        json={"assetId": "asset-999"},
        headers={"Authorization": "Bearer consumer-auth-token-2026"},
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["status"] == "rejected"
    assert "asset not found" in data["reason"]
