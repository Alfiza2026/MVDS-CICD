"""TC07 - Perform valid policy negotiation."""


def test_valid_policy_negotiation(provider_client):
    response = provider_client.post(
        "/negotiate",
        json={"assetId": "asset-001"},
        headers={"Authorization": "Bearer consumer-auth-token-2026"},
    )
    data = response.get_json()

    assert response.status_code == 200
    assert data["status"] == "accepted"
    assert data["contractId"] == "contract-001"
    assert data["policyId"] == "policy-001"
