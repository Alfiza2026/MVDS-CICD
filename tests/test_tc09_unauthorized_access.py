"""TC09 - Reject unauthorized access attempts."""


def test_negotiate_without_token(provider_client):
    """Negotiation should fail when no auth token is provided."""
    response = provider_client.post(
        "/negotiate",
        json={"assetId": "asset-001"},
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "rejected"
    assert "unauthorized" in data["reason"]


def test_negotiate_with_invalid_token(provider_client):
    """Negotiation should fail when an incorrect token is provided."""
    response = provider_client.post(
        "/negotiate",
        json={"assetId": "asset-001"},
        headers={"Authorization": "Bearer wrong-token-xyz"},
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "rejected"
    assert "invalid credentials" in data["reason"]


def test_transfer_without_token(provider_client):
    """Transfer should fail when no auth token is provided."""
    response = provider_client.post(
        "/transfer",
        json={"contractId": "contract-001"},
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "rejected"
    assert "unauthorised" in data["reason"]


def test_transfer_with_invalid_token(provider_client):
    """Transfer should fail when an incorrect token is provided."""
    response = provider_client.post(
        "/transfer",
        json={"contractId": "contract-001"},
        headers={"Authorization": "Bearer expired-token-000"},
    )

    assert response.status_code == 401
    data = response.get_json()
    assert data["status"] == "rejected"
    assert "unauthorised" in data["reason"]
