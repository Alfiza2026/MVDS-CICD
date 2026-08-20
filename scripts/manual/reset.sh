#!/bin/bash
# Reset script - tears down the mvds namespace between trials.
# Usage: bash scripts/manual/reset.sh

set -e

CLUSTER_NAME="mvds-cluster"
NAMESPACE="mvds"

echo "[$(date -Iseconds)] Resetting MVDS deployment..."

# Delete namespace (removes all resources within it)
if kubectl get namespace "$NAMESPACE" &>/dev/null; then
    echo "[$(date -Iseconds)] Deleting namespace: $NAMESPACE"
    kubectl delete namespace "$NAMESPACE" --timeout=60s
    echo "[$(date -Iseconds)] Namespace deleted"
else
    echo "[$(date -Iseconds)] Namespace $NAMESPACE does not exist, skipping"
fi

# Optionally delete the kind cluster entirely
if [ "$1" == "--full" ]; then
    echo "[$(date -Iseconds)] Deleting kind cluster: $CLUSTER_NAME"
    kind delete cluster --name "$CLUSTER_NAME"
    echo "[$(date -Iseconds)] Cluster deleted"
fi

echo "[$(date -Iseconds)] Reset complete. Ready for next trial."
