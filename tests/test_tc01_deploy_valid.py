"""TC01 - Deploy MVDS using valid configuration and images."""


def test_deploy_valid_services(provider_client, consumer_client):
    provider_resp = provider_client.get("/health")
    consumer_resp = consumer_client.get("/health")

    assert provider_resp.status_code == 200
    assert consumer_resp.status_code == 200
    assert provider_resp.get_json()["status"] == "healthy"
    assert consumer_resp.get_json()["status"] == "healthy"
