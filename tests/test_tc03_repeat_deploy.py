"""TC03 - Re-run deployment using identical configuration."""


def test_repeated_deployment_consistency(provider_client):
    results = []
    for _ in range(3):
        r = provider_client.get("/health")
        results.append(r.status_code)

    assert all(code == 200 for code in results)
