"""TC05 - Authenticate authorised provider and consumer."""


def test_authenticate_valid_consumer(provider_client):
    response = provider_client.post(
        "/negotiate",
        json={"assetId": "asset-001"},
        headers={"Authorization": "Bearer consumer-auth-token-2026"},
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "accepted"
