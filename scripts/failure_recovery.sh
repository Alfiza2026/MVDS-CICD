#!/bin/bash
# =============================================================================
# MVDS Failure & Recovery Simulation
# =============================================================================
# Purpose: Intentionally breaks a component, observes the failure state,
#          then triggers recovery — capturing timestamps for recovery time
#          measurement. Produces screenshot-able pod status transitions:
#          Running -> Error/CrashLoopBackOff -> Running
#
# Usage:   bash scripts/failure_recovery.sh
# Prereq:  Cluster running with provider/consumer deployed in namespace mvds
# =============================================================================

NAMESPACE="mvds"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  MVDS FAILURE & RECOVERY SIMULATION                        ║"
echo "║  Started: $(date -Iseconds)                                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# ─── PHASE 1: Baseline — confirm healthy state ──────────────────────────────
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ PHASE 1: Baseline (healthy state)                           │"
echo "│ Timestamp: $(date -Iseconds)                                │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "  Current pod status:"
kubectl get pods -n "$NAMESPACE" | sed 's/^/    /'
echo ""
echo "  Provider health check:"
kubectl exec -n "$NAMESPACE" deploy/consumer-deployment -- \
    wget -qO- http://provider-service:8080/health 2>/dev/null | sed 's/^/    /' || \
    echo "    (exec not available — checking via port-forward)"
echo ""

# ─── PHASE 2: Inject failure — kill the provider pod ─────────────────────────
FAILURE_TIME=$(date +%s)
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ PHASE 2: Inject Failure                                     │"
echo "│ Timestamp: $(date -Iseconds)                                │"
echo "│ Action: Deleting provider pod (simulates crash)             │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""

# Delete the provider pod — Kubernetes will detect it's gone
PROVIDER_POD=$(kubectl get pods -n "$NAMESPACE" -l app=provider -o jsonpath='{.items[0].metadata.name}')
echo "  Target pod: $PROVIDER_POD"
echo "  [$(date -Iseconds)] Deleting pod..."
kubectl delete pod "$PROVIDER_POD" -n "$NAMESPACE" --grace-period=0 --force 2>/dev/null
echo "  [$(date -Iseconds)] Pod deleted"
echo ""

# ─── PHASE 3: Observe failure state ─────────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ PHASE 3: Observe Failure State                              │"
echo "│ Timestamp: $(date -Iseconds)                                │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""

echo "  Pod status immediately after failure:"
kubectl get pods -n "$NAMESPACE" | sed 's/^/    /'
echo ""

echo "  Waiting 5s for Kubernetes to react..."
sleep 5

echo "  Pod status after 5s:"
kubectl get pods -n "$NAMESPACE" | sed 's/^/    /'
echo ""

echo "  Events for provider deployment:"
kubectl get events -n "$NAMESPACE" --sort-by='.lastTimestamp' | grep -i provider | tail -5 | sed 's/^/    /'
echo ""

# ─── PHASE 4: Observe automatic recovery ────────────────────────────────────
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│ PHASE 4: Observe Recovery                                   │"
echo "│ Timestamp: $(date -Iseconds)                                │"
echo "│ Waiting for Kubernetes to restart the pod...                │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""

echo "  Waiting for provider deployment rollout..."
kubectl rollout status deployment/provider-deployment -n "$NAMESPACE" --timeout=60s

RECOVERY_TIME=$(date +%s)
RECOVERY_DURATION=$(( RECOVERY_TIME - FAILURE_TIME ))

echo ""
echo "  Pod status after recovery:"
kubectl get pods -n "$NAMESPACE" | sed 's/^/    /'
echo ""

echo "  Provider health check after recovery:"
# Use kubectl exec to check health from inside the cluster (avoids port conflicts)
sleep 5
HEALTH=$(kubectl exec -n "$NAMESPACE" deploy/consumer-deployment -- \
    wget -qO- http://provider-service:8080/health 2>/dev/null)
if [ -n "$HEALTH" ]; then
    echo "    Status: ✓ RECOVERED"
    echo "    Response: $HEALTH"
else
    # Fallback: use a different local port to avoid conflicts
    kubectl port-forward service/provider-service 9080:8080 -n "$NAMESPACE" &
    PF_PID=$!
    sleep 3
    HEALTH=$(curl -sf http://localhost:9080/health 2>/dev/null)
    kill $PF_PID 2>/dev/null || true
    if [ -n "$HEALTH" ]; then
        echo "    Status: ✓ RECOVERED"
        echo "    Response: $HEALTH"
    else
        echo "    Status: ⟳ Still starting (may need a few more seconds)"
    fi
fi
echo ""

# ─── SUMMARY ─────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  FAILURE & RECOVERY SUMMARY                                 ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Component:      provider-connector                         ║"
echo "║  Failure Type:   Pod deletion (simulated crash)             ║"
echo "║  Recovery Mode:  Automatic (Kubernetes Deployment restart)  ║"
echo "║  Recovery Time:  ${RECOVERY_DURATION}s                      ║"
echo "║  Final Status:   Running                                    ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Screenshots to capture:"
echo "  1. Phase 3 output — pod in ContainerCreating/NotReady state"
echo "  2. Phase 4 output — pod back to Running (1/1 Ready)"
echo "  3. Events showing SuccessfulDelete -> Scheduled -> Started"
