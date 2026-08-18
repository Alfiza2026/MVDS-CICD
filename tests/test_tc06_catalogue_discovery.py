"""TC06 - Execute catalogue/metadata discovery."""


def test_catalogue_discovery(provider_client):
    response = provider_client.get("/catalogue")
    data = response.get_json()

    assert response.status_code == 200
    assert "assets" in data
    assert len(data["assets"]) > 0
    assert data["assets"][0]["id"] == "asset-001"
