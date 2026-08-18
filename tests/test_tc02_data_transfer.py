"""TC02 - Execute provider-to-consumer data transfer."""

from unittest.mock import patch, MagicMock


def test_provider_to_consumer_transfer(consumer_client, consumer_module):
    with patch.object(consumer_module.requests, "get") as mock_get, \
         patch.object(consumer_module.requests, "post") as mock_post:

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"assets": [{"id": "asset-001"}], "timestamp": 1.0}
        )

        mock_negotiate = MagicMock(
            status_code=200,
            json=lambda: {"status": "accepted", "contractId": "contract-001", "assetId": "asset-001"}
        )
        mock_transfer = MagicMock(
            status_code=200,
            json=lambda: {"status": "success", "data": {"temperature": 22.5}, "transferId": "transfer-001", "timestamp": 1.0}
        )
        mock_post.side_effect = [mock_negotiate, mock_transfer]

        response = consumer_client.get("/run-full-flow")
        data = response.get_json()

        assert response.status_code == 200
        assert data["success"] is True
        assert data["results"]["transfer"]["success"] is True
