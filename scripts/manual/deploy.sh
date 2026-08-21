#!/bin/bash
# =============================================================================
# MVDS Manual Deployment Baseline Script
# =============================================================================
# Purpose: Reproduces the exact CI/CD pipeline steps manually with timestamps
#          at each step, producing comparable timing data for dissertation
#          deployment-time comparison (automated vs manual).
#
# Usage:   bash scripts/manual/deploy.sh [TRIAL_ID]
# Output:  Timestamped log to stdout + results/metrics.csv row
# =============================================================================

set -e

TRIAL_ID="${1:-manual-$(date +%s)}"
CLUSTER_NAME="mvds-cluster"
NAMESPACE="mvds"
LOG_FILE="results/manual-deploy-${TRIAL_ID}.log"

mkdir -p results

# Tee all output to log file for screenshot evidence
exec > >(tee -a "$LOG_FILE") 2>&1

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  MVDS MANUAL DEPLOYMENT BASELINE                           ║"
echo "║  Trial ID: $TRIAL_ID"
echo "║  Started:  $(date -Iseconds)"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

DEPLOY_START=$(date +%s.%N)

# ─── STEP 1: Install Dependencies & Run Tests ────────────────────────────────
STEP1_START=$(date +%s.%N)
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ STEP 1: Build and Test                                      │"
echo "│ Start: $(date -Iseconds)                                    │"
echo "└─────────────────────────────────────────────────────────────┘"

pip install flask requests pytest pyyaml prometheus_client --quiet
python -m pytest tests/ -v --junitxml=results/pytest-output.xml

STEP1_END=$(date +%s.%N)
STEP1_DURATION=$(echo "$STEP1_END - $STEP1_START" | bc)
echo ">>> Step 1 completed in ${STEP1_DURATION}s"
echo ""

# ─── STEP 2: Security Scan ───────────────────────────────────────────────────
STEP2_START=$(date +%s.%N)
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ STEP 2: Security Scan                                       │"
echo "│ Start: $(date -Iseconds)                                    │"
echo "└─────────────────────────────────────────────────────────────┘"

if command -v trivy &> /dev/null; then
    trivy fs src/provider/ --exit-code 1 --severity CRITICAL
    trivy fs src/consumer/ --exit-code 1 --severity CRITICAL
else
    echo "[SKIP] Trivy not installed locally — skipped (CI handles this)"
fi

STEP2_END=$(date +%s.%N)
STEP2_DURATION=$(echo "$STEP2_END - $STEP2_START" | bc)
echo ">>> Step 2 completed in ${STEP2_DURATION}s"
echo ""

# ─── STEP 3: Build Docker Images ────────────────────────────────────────────
STEP3_START=$(date +%s.%N)
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ STEP 3: Build Docker Images                                 │"
echo "│ Start: $(date -Iseconds)                                    │"
echo "└─────────────────────────────────────────────────────────────┘"

docker build -t provider-connector:latest src/provider/
docker build -t consumer-connector:latest src/consumer/
echo "Images built:"
docker images | grep -E "provider-connector|consumer-connector"

STEP3_END=$(date +%s.%N)
STEP3_DURATION=$(echo "$STEP3_END - $STEP3_START" | bc)
echo ">>> Step 3 completed in ${STEP3_DURATION}s"
echo ""

# ─── STEP 4: Validate Kubernetes Manifests ───────────────────────────────────
STEP4_START=$(date +%s.%N)
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ STEP 4: Validate Manifests                                  │"
echo "│ Start: $(date -Iseconds)                                    │"
echo "└─────────────────────────────────────────────────────────────┘"

python -c "
import yaml
with open('k8s/provider/deployment.yaml') as f:
    docs = list(yaml.safe_load_all(f))
print(f'  Provider manifest valid - {len(docs)} documents')
"
python -c "
import yaml
with open('k8s/consumer/deployment.yaml') as f:
    docs = list(yaml.safe_load_all(f))
print(f'  Consumer manifest valid - {len(docs)} documents')
"

STEP4_END=$(date +%s.%N)
STEP4_DURATION=$(echo "$STEP4_END - $STEP4_START" | bc)
echo ">>> Step 4 completed in ${STEP4_DURATION}s"
echo ""

# ─── STEP 5: Deploy to Kubernetes ───────────────────────────────────────────
STEP5_START=$(date +%s.%N)
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ STEP 5: Deploy to Kubernetes                                │"
echo "│ Start: $(date -Iseconds)                                    │"
echo "└─────────────────────────────────────────────────────────────┘"

# Create cluster if needed
if ! kind get clusters 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    echo "  Creating kind cluster..."
    kind create cluster --name "$CLUSTER_NAME"
fi

echo "  Loading images into kind..."
kind load docker-image provider-connector:latest --name "$CLUSTER_NAME"
kind load docker-image consumer-connector:latest --name "$CLUSTER_NAME"

echo "  Creating namespace..."
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

echo "  Deploying metrics-server..."
kubectl apply -f k8s/monitoring/metrics-server.yaml
kubectl rollout status deployment/metrics-server -n kube-system --timeout=60s || true

echo "  Applying provider deployment..."
echo "  [$(date -Iseconds)] kubectl apply -f k8s/provider/deployment.yaml"
kubectl apply -f k8s/provider/deployment.yaml

echo "  Applying consumer deployment..."
echo "  [$(date -Iseconds)] kubectl apply -f k8s/consumer/deployment.yaml"
kubectl apply -f k8s/consumer/deployment.yaml

echo "  Waiting for provider rollout..."
kubectl rollout status deployment/provider-deployment -n "$NAMESPACE" --timeout=120s

echo "  Waiting for consumer rollout..."
kubectl rollout status deployment/consumer-deployment -n "$NAMESPACE" --timeout=120s

echo "  [$(date -Iseconds)] All pods ready"
kubectl get pods -n "$NAMESPACE"

STEP5_END=$(date +%s.%N)
STEP5_DURATION=$(echo "$STEP5_END - $STEP5_START" | bc)
echo ">>> Step 5 completed in ${STEP5_DURATION}s"
echo ""

# ─── STEP 6: Deploy Monitoring Stack ────────────────────────────────────────
STEP6_START=$(date +%s.%N)
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ STEP 6: Deploy Monitoring Stack                             │"
echo "│ Start: $(date -Iseconds)                                    │"
echo "└─────────────────────────────────────────────────────────────┘"

echo "  Loading monitoring images..."
docker pull prom/prometheus:v2.51.0 2>/dev/null || true
docker pull grafana/grafana:10.4.0 2>/dev/null || true
kind load docker-image prom/prometheus:v2.51.0 --name "$CLUSTER_NAME"
kind load docker-image grafana/grafana:10.4.0 --name "$CLUSTER_NAME"

echo "  [$(date -Iseconds)] kubectl apply -f k8s/monitoring/prometheus-deployment.yaml"
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml

echo "  [$(date -Iseconds)] kubectl apply -f k8s/monitoring/grafana-deployment.yaml"
kubectl apply -f k8s/monitoring/grafana-deployment.yaml

kubectl rollout status deployment/prometheus-deployment -n "$NAMESPACE" --timeout=180s
kubectl rollout status deployment/grafana-deployment -n "$NAMESPACE" --timeout=180s

echo "  [$(date -Iseconds)] Monitoring stack ready"

STEP6_END=$(date +%s.%N)
STEP6_DURATION=$(echo "$STEP6_END - $STEP6_START" | bc)
echo ">>> Step 6 completed in ${STEP6_DURATION}s"
echo ""

# ─── STEP 7: Functional Validation ──────────────────────────────────────────
STEP7_START=$(date +%s.%N)
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ STEP 7: Functional Validation                               │"
echo "│ Start: $(date -Iseconds)                                    │"
echo "└─────────────────────────────────────────────────────────────┘"

kubectl port-forward service/provider-service 8080:8080 -n "$NAMESPACE" &
PF_PROVIDER=$!
kubectl port-forward service/consumer-service 8081:8081 -n "$NAMESPACE" &
PF_CONSUMER=$!
sleep 10

echo "  Testing provider health..."
curl -sf -H "X-Trial-Id: $TRIAL_ID" http://localhost:8080/health | python -m json.tool
echo "  Testing consumer health..."
curl -sf -H "X-Trial-Id: $TRIAL_ID" http://localhost:8081/health | python -m json.tool
echo "  Testing full flow..."
curl -sf -H "X-Trial-Id: $TRIAL_ID" http://localhost:8081/run-full-flow | python -m json.tool

kill $PF_PROVIDER $PF_CONSUMER 2>/dev/null || true

STEP7_END=$(date +%s.%N)
STEP7_DURATION=$(echo "$STEP7_END - $STEP7_START" | bc)
echo ">>> Step 7 completed in ${STEP7_DURATION}s"
echo ""

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
DEPLOY_END=$(date +%s.%N)
TOTAL_TIME=$(echo "$DEPLOY_END - $DEPLOY_START" | bc)

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  DEPLOYMENT SUMMARY                                         ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Trial ID:          $TRIAL_ID"
echo "║  Condition:         manual"
echo "║  ──────────────────────────────────────────────────────────"
echo "║  Step 1 (Test):     ${STEP1_DURATION}s"
echo "║  Step 2 (Scan):     ${STEP2_DURATION}s"
echo "║  Step 3 (Build):    ${STEP3_DURATION}s"
echo "║  Step 4 (Validate): ${STEP4_DURATION}s"
echo "║  Step 5 (Deploy):   ${STEP5_DURATION}s"
echo "║  Step 6 (Monitor):  ${STEP6_DURATION}s"
echo "║  Step 7 (Verify):   ${STEP7_DURATION}s"
echo "║  ──────────────────────────────────────────────────────────"
echo "║  TOTAL TIME:        ${TOTAL_TIME}s"
echo "║  Finished:          $(date -Iseconds)"
echo "╚══════════════════════════════════════════════════════════════╝"

# Record to metrics CSV
python scripts/collect_metrics.py \
    --trial-id "$TRIAL_ID" \
    --condition manual \
    --start-time "$DEPLOY_START" \
    --end-time "$DEPLOY_END" \
    --pytest-result results/pytest-output.xml

echo ""
echo "Log saved to: $LOG_FILE"
