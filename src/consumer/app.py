from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import requests as http_requests
import time
import json
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

PROVIDER_URL = "http://provider-service:8080"
AUTH_TOKEN = "consumer-auth-token-2026"

# Prometheus metrics
REQUEST_COUNT = Counter(
    "consumer_requests_total",
    "Total requests to consumer",
    ["method", "endpoint", "status"]
)
REQUEST_LATENCY = Histogram(
    "consumer_request_duration_seconds",
    "Request latency in seconds",
    ["endpoint"]
)
CONSUMER_UP = Gauge(
    "consumer_up",
    "Consumer connector availability (1=up, 0=down)"
)
CONSUMER_UP.set(1)


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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "component": "consumer-connector"}), 200


@app.route("/metrics", methods=["GET"])
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.route("/discover", methods=["GET"])
def discover():
    with REQUEST_LATENCY.labels(endpoint="/discover").time():
        try:
            response = http_requests.get(f"{PROVIDER_URL}/catalogue", timeout=10)
            if response.status_code == 200:
                _structured_log("discover", "success")
                return jsonify({
                    "status": "success",
                    "catalogue": response.json(),
                    "timestamp": time.time()
                }), 200
            else:
                _structured_log("discover", "failed", {"provider_status": response.status_code})
                return jsonify({
                    "status": "failed",
                    "reason": f"provider returned {response.status_code}"
                }), 502
        except http_requests.exceptions.ConnectionError:
            _structured_log("discover", "error", {"reason": "provider unreachable"})
            return jsonify({"status": "error", "reason": "provider unreachable"}), 503


@app.route("/negotiate", methods=["POST"])
def negotiate():
    with REQUEST_LATENCY.labels(endpoint="/negotiate").time():
        body = request.get_json()
        asset_id = body.get("assetId", "asset-001")
        try:
            response = http_requests.post(
                f"{PROVIDER_URL}/negotiate",
                json={"assetId": asset_id},
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                timeout=10
            )
            _structured_log("negotiate", "success" if response.status_code == 200 else "failed")
            return jsonify(response.json()), response.status_code
        except http_requests.exceptions.ConnectionError:
            _structured_log("negotiate", "error", {"reason": "provider unreachable"})
            return jsonify({"status": "error", "reason": "provider unreachable"}), 503


@app.route("/transfer", methods=["POST"])
def transfer():
    with REQUEST_LATENCY.labels(endpoint="/transfer").time():
        body = request.get_json()
        contract_id = body.get("contractId", "contract-001")
        try:
            response = http_requests.post(
                f"{PROVIDER_URL}/transfer",
                json={"contractId": contract_id},
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                timeout=10
            )
            _structured_log("transfer", "success" if response.status_code == 200 else "failed")
            return jsonify(response.json()), response.status_code
        except http_requests.exceptions.ConnectionError:
            _structured_log("transfer", "error", {"reason": "provider unreachable"})
            return jsonify({"status": "error", "reason": "provider unreachable"}), 503


@app.route("/run-full-flow", methods=["GET"])
def run_full_flow():
    results = {}
    start_time = time.time()

    try:
        r = http_requests.get(f"{PROVIDER_URL}/catalogue", timeout=10)
        results["discovery"] = {"status": r.status_code, "success": r.status_code == 200}
    except Exception as e:
        results["discovery"] = {"status": "error", "success": False, "reason": str(e)}
        return jsonify({"flow": "failed", "step": "discovery", "results": results}), 503

    try:
        r = http_requests.post(
            f"{PROVIDER_URL}/negotiate",
            json={"assetId": "asset-001"},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=10
        )
        results["negotiation"] = {"status": r.status_code, "success": r.status_code == 200}
        contract_id = r.json().get("contractId", "contract-001")
    except Exception as e:
        results["negotiation"] = {"status": "error", "success": False, "reason": str(e)}
        return jsonify({"flow": "failed", "step": "negotiation", "results": results}), 503

    try:
        r = http_requests.post(
            f"{PROVIDER_URL}/transfer",
            json={"contractId": contract_id},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=10
        )
        results["transfer"] = {"status": r.status_code, "success": r.status_code == 200}
    except Exception as e:
        results["transfer"] = {"status": "error", "success": False, "reason": str(e)}
        return jsonify({"flow": "failed", "step": "transfer", "results": results}), 503

    end_time = time.time()
    all_success = all(v["success"] for v in results.values())

    return jsonify({
        "flow": "completed" if all_success else "partial",
        "success": all_success,
        "duration_seconds": round(end_time - start_time, 3),
        "results": results,
        "timestamp": end_time
    }), 200 if all_success else 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081)
