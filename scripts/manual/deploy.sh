#!/bin/bash
# Manual deployment script - reproduces the CI/CD pipeline steps locally.
# Usage: bash scripts/manual/deploy.sh [TRIAL_ID]
# Measures deployment time with timestamps at each step.

set -e

TRIAL_ID="${1:-manual-$(date +%s)}"
CLUSTER_NAME="mvds-cluster"
NAMESPACE="mvds"

echo "============================================"
echo "MVDS Manual Deployment - Trial: $TRIAL_ID"
echo "============================================"

DEPLOY_START=$(date +%s.%N)

# --- Step 1: Build and Test ---
STEP_START=$(date +%s.%N)
echo ""
echo "[$(date -Iseconds)] STEP 1: Build and Test - START"

pip install flask requests pytest pyyaml prometheus_client --quiet
python -m pytest tests/ -v --junitxml=results/pytest-output.xml

STEP_END=$(date +%s.%N)
echo "[$(date -Iseconds)] STEP 1: Build and Test - END ($(echo "$STEP_END - $STEP_START" | bc)s)"

# --- Step 2: Security Scan ---
STEP_START=$(date +%s.%N)
echo ""
echo "[$(date -Iseconds)] STEP 2: Security Scan - START"

trivy fs src/provider/ --exit-code 1 --severity CRITICAL
trivy fs src/consumer/ --exit-code 1 --severity CRITICAL

STEP_END=$(date +%s.%N)
echo "[$(date -Iseconds)] STEP 2: Security Scan - END ($(echo "$STEP_END - $STEP_START" | bc)s)"

# --- Step 3: Build Docker Images ---
STEP_START=$(date +%s.%N)
echo ""
echo "[$(date -Iseconds)] STEP 3: Build Docker Images - START"

docker build -t provider-connector:latest src/provider/
docker build -t consumer-connector:latest src/consumer/
docker images | grep -E "provider-connector|consumer-connector"

STEP_END=$(date +%s.%N)
echo "[$(date -Iseconds)] STEP 3: Build Docker Images - END ($(echo "$STEP_END - $STEP_START" | bc)s)"

# --- Step 4: Validate Kubernetes Manifests ---
STEP_START=$(date +%s.%N)
echo ""
echo "[$(date -Iseconds)] STEP 4: Validate Manifests - START"

python -c "
import yaml
with open('k8s/provider/deployment.yaml') as f:
    docs = list(yaml.safe_load_all(f))
print(f'Provider manifest valid - {len(docs)} documents')
"

python -c "
import yaml
with open('k8s/consumer/deployment.yaml') as f:
    docs = list(yaml.safe_load_all(f))
print(f'Consumer manifest valid - {len(docs)} documents')
"

STEP_END=$(date +%s.%N)
echo "[$(date -Iseconds)] STEP 4: Validate Manifests - END ($(echo "$STEP_END - $STEP_START" | bc)s)"

# --- Step 5: Deploy to Kubernetes ---
STEP_START=$(date +%s.%N)
echo ""
echo "[$(date -Iseconds)] STEP 5: Deploy to Kubernetes - START"

# Create cluster if it doesn't exist
if ! kind get clusters | grep -q "$CLUSTER_NAME"; then
    kind create cluster --name "$CLUSTER_NAME"
fi

# Load images into kind
kind load docker-image provider-connector:latest --name "$CLUSTER_NAME"
kind load docker-image consumer-connector:latest --name "$CLUSTER_NAME"

# Create namespace if it doesn't exist
kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

# Deploy metrics-server for kubectl top support
kubectl apply -f k8s/monitoring/metrics-server.yaml
kubectl rollout status deployment/metrics-server -n kube-system --timeout=60s
sleep 30

# Deploy
kubectl apply -f k8s/provider/deployment.yaml
kubectl apply -f k8s/consumer/deployment.yaml

# Wait for rollout
kubectl rollout status deployment/provider-deployment -n "$NAMESPACE" --timeout=120s
kubectl rollout status deployment/consumer-deployment -n "$NAMESPACE" --timeout=120s

STEP_END=$(date +%s.%N)
echo "[$(date -Iseconds)] STEP 5: Deploy to Kubernetes - END ($(echo "$STEP_END - $STEP_START" | bc)s)"

# --- Step 6: Functional Validation ---
STEP_START=$(date +%s.%N)
echo ""
echo "[$(date -Iseconds)] STEP 6: Functional Validation - START"

kubectl port-forward service/provider-service 8080:8080 -n "$NAMESPACE" &
PF_PROVIDER=$!
kubectl port-forward service/consumer-service 8081:8081 -n "$NAMESPACE" &
PF_CONSUMER=$!
sleep 10

curl -f -H "X-Trial-Id: $TRIAL_ID" http://localhost:8080/health
curl -f -H "X-Trial-Id: $TRIAL_ID" http://localhost:8081/health
curl -f -H "X-Trial-Id: $TRIAL_ID" http://localhost:8081/run-full-flow

kill $PF_PROVIDER $PF_CONSUMER 2>/dev/null || true

STEP_END=$(date +%s.%N)
echo "[$(date -Iseconds)] STEP 6: Functional Validation - END ($(echo "$STEP_END - $STEP_START" | bc)s)"

# --- Collect Metrics ---
DEPLOY_END=$(date +%s.%N)
TOTAL_TIME=$(echo "$DEPLOY_END - $DEPLOY_START" | bc)

echo ""
echo "============================================"
echo "DEPLOYMENT COMPLETE"
echo "Total time: ${TOTAL_TIME}s"
echo "============================================"

python scripts/collect_metrics.py \
    --trial-id "$TRIAL_ID" \
    --condition manual \
    --start-time "$DEPLOY_START" \
    --end-time "$DEPLOY_END" \
    --pytest-result results/pytest-output.xml
