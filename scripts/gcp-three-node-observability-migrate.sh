#!/usr/bin/env bash
# Fresh-redeploy observability onto kuberag-worker-observability.
# DESTRUCTIVE to existing observability PVCs (short retention telemetry only).
# Does not touch PostgreSQL, RAG, Prefect, or application PVCs.
set -euo pipefail

KUBECONFIG="${KUBECONFIG:-${HOME}/.kube/kuberag-gcp.yaml}"
export KUBECONFIG
NAMESPACE="${OBSERVABILITY_NAMESPACE:-observability}"
VALUES_DIR="${OBSERVABILITY_VALUES_DIR:-deploy/helm/observability}"
THREE_NODE_DIR="${VALUES_DIR}/three-node"
KUSTOMIZE_DIR="${OBSERVABILITY_KUSTOMIZE:-observability}"

KUBE_PROMETHEUS_STACK_VERSION="${KUBE_PROMETHEUS_STACK_VERSION:-87.21.0}"
LOKI_CHART_VERSION="${LOKI_CHART_VERSION:-7.2.0}"
TEMPO_CHART_VERSION="${TEMPO_CHART_VERSION:-1.24.4}"
PYROSCOPE_CHART_VERSION="${PYROSCOPE_CHART_VERSION:-2.2.0}"
OTEL_COLLECTOR_CHART_VERSION="${OTEL_COLLECTOR_CHART_VERSION:-0.165.0}"

echo "==> Preflight: observability worker Ready?"
kubectl get node -l kuberag.io/role=observability --no-headers | grep -q Ready

echo "==> Uninstall Helm releases (Secrets for Grafana/Slack are retained)"
helm uninstall kuberag-otel -n "${NAMESPACE}" --ignore-not-found
helm uninstall kuberag-pyroscope -n "${NAMESPACE}" --ignore-not-found
helm uninstall kuberag-tempo -n "${NAMESPACE}" --ignore-not-found
helm uninstall kuberag-loki -n "${NAMESPACE}" --ignore-not-found
helm uninstall kuberag-monitoring -n "${NAMESPACE}" --ignore-not-found

echo "==> Wait for StatefulSets/Deployments to leave"
kubectl -n "${NAMESPACE}" delete statefulset --all --ignore-not-found --wait=true --timeout=5m || true
kubectl -n "${NAMESPACE}" delete deployment --all --ignore-not-found --wait=true --timeout=5m || true
kubectl -n "${NAMESPACE}" delete pods --all --ignore-not-found --force --grace-period=0 2>/dev/null || true

echo "==> Delete node-local observability PVCs (telemetry history reset)"
kubectl -n "${NAMESPACE}" delete pvc --all --wait=true --timeout=5m

echo "==> Reinstall with observability nodeSelector overlays"
helm upgrade --install kuberag-monitoring prometheus-community/kube-prometheus-stack \
  --version "${KUBE_PROMETHEUS_STACK_VERSION}" \
  --namespace "${NAMESPACE}" \
  --create-namespace \
  --values "${VALUES_DIR}/kube-prometheus-stack-values.yaml" \
  --values "${THREE_NODE_DIR}/kube-prometheus-stack-node-selector.yaml"

helm upgrade --install kuberag-loki grafana/loki \
  --version "${LOKI_CHART_VERSION}" \
  --namespace "${NAMESPACE}" \
  --create-namespace \
  --values "${VALUES_DIR}/loki-values.yaml" \
  --values "${THREE_NODE_DIR}/loki-node-selector.yaml"

helm upgrade --install kuberag-tempo grafana/tempo \
  --version "${TEMPO_CHART_VERSION}" \
  --namespace "${NAMESPACE}" \
  --create-namespace \
  --values "${VALUES_DIR}/tempo-values.yaml" \
  --values "${THREE_NODE_DIR}/tempo-node-selector.yaml"

helm upgrade --install kuberag-pyroscope grafana/pyroscope \
  --version "${PYROSCOPE_CHART_VERSION}" \
  --namespace "${NAMESPACE}" \
  --create-namespace \
  --values "${VALUES_DIR}/pyroscope-values.yaml" \
  --values "${THREE_NODE_DIR}/pyroscope-node-selector.yaml"

helm upgrade --install kuberag-otel open-telemetry/opentelemetry-collector \
  --version "${OTEL_COLLECTOR_CHART_VERSION}" \
  --namespace "${NAMESPACE}" \
  --create-namespace \
  --values "${VALUES_DIR}/otel-collector-values.yaml" \
  --values "${THREE_NODE_DIR}/otel-collector-node-selector.yaml"

echo "==> Re-apply project ServiceMonitors/dashboards/alerts"
kubectl apply -k "${KUSTOMIZE_DIR}"

echo "==> Wait for Ready"
kubectl -n "${NAMESPACE}" wait --for=condition=Available deployment/kuberag-monitoring-grafana --timeout=15m
kubectl -n "${NAMESPACE}" wait --for=condition=Available deployment/kuberag-otel-collector --timeout=15m
kubectl -n "${NAMESPACE}" rollout status statefulset/kuberag-loki --timeout=15m
kubectl -n "${NAMESPACE}" rollout status statefulset/kuberag-tempo --timeout=15m
kubectl -n "${NAMESPACE}" rollout status statefulset/kuberag-pyroscope --timeout=15m
kubectl -n "${NAMESPACE}" rollout status statefulset/prometheus-kuberag-monitoring-kube-pr-prometheus --timeout=15m

echo "==> Placement check"
kubectl -n "${NAMESPACE}" get pods -o wide
echo "DONE"
