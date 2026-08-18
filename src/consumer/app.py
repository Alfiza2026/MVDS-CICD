from flask import Flask, jsonify, request
import requests
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

PROVIDER_URL = "http://provider-service:8080"
AUTH_TOKEN = "consumer-auth-token-2026"


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "component": "consumer-connector"}), 200


@app.route("/discover", methods=["GET"])
def discover():
    try:
        response = requests.get(f"{PROVIDER_URL}/catalogue", timeout=10)
        if response.status_code == 200:
            return jsonify({
                "status": "success",
                "catalogue": response.json(),
                "timestamp": time.time()
            }), 200
        else:
            return jsonify({
                "status": "failed",
                "reason": f"provider returned {response.status_code}"
            }), 502
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "error", "reason": "provider unreachable"}), 503


@app.route("/negotiate", methods=["POST"])
def negotiate():
    body = request.get_json()
    asset_id = body.get("assetId", "asset-001")
    try:
        response = requests.post(
            f"{PROVIDER_URL}/negotiate",
            json={"assetId": asset_id},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "error", "reason": "provider unreachable"}), 503


@app.route("/transfer", methods=["POST"])
def transfer():
    body = request.get_json()
    contract_id = body.get("contractId", "contract-001")
    try:
        response = requests.post(
            f"{PROVIDER_URL}/transfer",
            json={"contractId": contract_id},
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            timeout=10
        )
        return jsonify(response.json()), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "error", "reason": "provider unreachable"}), 503


@app.route("/run-full-flow", methods=["GET"])
def run_full_flow():
    results = {}
    start_time = time.time()

    try:
        r = requests.get(f"{PROVIDER_URL}/catalogue", timeout=10)
        results["discovery"] = {"status": r.status_code, "success": r.status_code == 200}
    except Exception as e:
        results["discovery"] = {"status": "error", "success": False, "reason": str(e)}
        return jsonify({"flow": "failed", "step": "discovery", "results": results}), 503

    try:
        r = requests.post(
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
        r = requests.post(
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
