from flask import Flask, jsonify, request
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

DATA_ASSET = {
    "id": "asset-001",
    "name": "Research Dataset Alpha",
    "description": "Structured dataset for MVDS data exchange experiment",
    "data": {"temperature": 22.5, "humidity": 60, "pressure": 1013.25}
}

POLICY = {
    "id": "policy-001",
    "assetId": "asset-001",
    "permission": "USE",
    "constraint": "authenticated-consumer-only"
}

VALID_TOKEN = "consumer-auth-token-2026"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "component": "provider-connector"}), 200


@app.route("/catalogue", methods=["GET"])
def catalogue():
    logging.info("Catalogue discovery request received")
    return jsonify({"assets": [DATA_ASSET], "timestamp": time.time()}), 200


@app.route("/negotiate", methods=["POST"])
def negotiate():
    body = request.get_json()
    token = request.headers.get("Authorization")

    if token != f"Bearer {VALID_TOKEN}":
        return jsonify({"status": "rejected", "reason": "invalid credentials"}), 401

    if body.get("assetId") != POLICY["assetId"]:
        return jsonify({"status": "rejected", "reason": "asset not found"}), 404

    return jsonify({
        "status": "accepted",
        "contractId": "contract-001",
        "assetId": body.get("assetId")
    }), 200


@app.route("/transfer", methods=["POST"])
def transfer():
    body = request.get_json()
    token = request.headers.get("Authorization")

    if token != f"Bearer {VALID_TOKEN}":
        return jsonify({"status": "rejected", "reason": "unauthorised"}), 401

    if body.get("contractId") != "contract-001":
        return jsonify({"status": "rejected", "reason": "invalid contract"}), 400

    return jsonify({
        "status": "success",
        "data": DATA_ASSET["data"],
        "transferId": "transfer-001",
        "timestamp": time.time()
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
