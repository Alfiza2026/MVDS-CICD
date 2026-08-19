"""TC13 - Provider handles rapid sequential requests without data corruption."""


def test_rapid_catalogue_requests(provider_client):
    """Provider should serve many catalogue requests consistently."""
    results = []
    for _ in range(20):
        response = provider_client.get("/catalogue")
        results.append((response.status_code, response.get_json()))

    for status_code, data in results:
        assert status_code == 200
        assert len(data["assets"]) == 1
        assert data["assets"][0]["id"] == "asset-001"


def test_rapid_negotiate_requests(provider_client):
    """Provider should handle many negotiate requests without state drift."""
    results = []
    for _ in range(20):
        response = provider_client.post(
            "/negotiate",
            json={"assetId": "asset-001"},
            headers={"Authorization": "Bearer consumer-auth-token-2026"},
        )
        results.append((response.status_code, response.get_json()))

    for status_code, data in results:
        assert status_code == 200
        assert data["status"] == "accepted"
        assert data["contractId"] == "contract-001"


def test_rapid_mixed_valid_and_invalid(provider_client):
    """Provider should correctly reject invalid tokens even under load."""
    results = []
    for i in range(20):
        valid = i % 2 == 0
        token = "consumer-auth-token-2026" if valid else "bad-token"
        response = provider_client.post(
            "/negotiate",
            json={"assetId": "asset-001"},
            headers={"Authorization": f"Bearer {token}"},
        )
        results.append((valid, response.status_code))

    for was_valid, status_code in results:
        if was_valid:
            assert status_code == 200
        else:
            assert status_code == 401
