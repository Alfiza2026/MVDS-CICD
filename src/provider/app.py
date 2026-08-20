from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import time
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "provider_requests_total",
    "Total requests to provider",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "provider_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint"]
)
PROVIDER_UP = Gauge(
    "provider_up",
    "Provider connector availability (1=up, 0=down)"
)
PROVIDER_UP.set(1)


@app.after_request
def track_metrics(response):
    if request.path != "/metrics":
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.path,
            status=response.status_code
        ).inc()
    return response


def _structured_log(event_type, outcome, extra=None):
    """Emit a structured JSON log line."""
    trial_id = request.headers.get("X-Trial-Id", "manual")
    log_entry = {
        "trial_id": trial_id,
        "event_type": event_type,
        "outcome": outcome,
        "timestamp": time.time()
    }
    if extra:
        log_entry.update(extra)
    logging.info(json.dumps(log_entry))

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


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/catalogue", methods=["GET"])
def catalogue():
    with REQUEST_LATENCY.labels(endpoint="/catalogue").time():
        logging.info("Catalogue discovery request received")
        return jsonify({"assets": [DATA_ASSET], "timestamp": time.time()}), 200


@app.route("/negotiate", methods=["POST"])
def negotiate():
    with REQUEST_LATENCY.labels(endpoint="/negotiate").time():
        body = request.get_json()
        token = request.headers.get("Authorization")

        if token != f"Bearer {VALID_TOKEN}":
            _structured_log("negotiate", "rejected", {"reason": "invalid credentials"})
            return jsonify({"status": "rejected", "reason": "invalid credentials"}), 401

        if body.get("assetId") != POLICY["assetId"]:
            _structured_log("negotiate", "rejected", {"reason": "asset not found"})
            return jsonify({"status": "rejected", "reason": "asset not found"}), 404

        _structured_log("negotiate", "accepted", {"assetId": body.get("assetId")})
        return jsonify({
            "status": "accepted",
            "contractId": "contract-001",
            "policyId": POLICY["id"],
            "assetId": body.get("assetId")
        }), 200


@app.route("/transfer", methods=["POST"])
def transfer():
    with REQUEST_LATENCY.labels(endpoint="/transfer").time():
        body = request.get_json()
        token = request.headers.get("Authorization")

        if token != f"Bearer {VALID_TOKEN}":
            _structured_log("transfer", "rejected", {"reason": "unauthorised"})
            return jsonify({"status": "rejected", "reason": "unauthorised"}), 401

        if body.get("contractId") != "contract-001":
            _structured_log("transfer", "rejected", {"reason": "invalid contract"})
            return jsonify({"status": "rejected", "reason": "invalid contract"}), 400

        _structured_log("transfer", "success", {"contractId": body.get("contractId")})
        return jsonify({
            "status": "success",
            "data": DATA_ASSET["data"],
            "transferId": "transfer-001",
            "timestamp": time.time()
        }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
