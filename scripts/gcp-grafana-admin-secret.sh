#!/usr/bin/env bash
# Create the Grafana administrator secret in-cluster without printing it.
set -euo pipefail

KUBECONFIG="${KUBECONFIG:-${GCP_KUBECONFIG:-$HOME/.kube/kuberag-gcp.yaml}}"
export KUBECONFIG

namespace="${OBSERVABILITY_NAMESPACE:-observability}"
secret_name="${GRAFANA_ADMIN_SECRET:-kuberag-grafana-admin}"

if kubectl -n "$namespace" get secret "$secret_name" >/dev/null 2>&1; then
  echo "secret ${namespace}/${secret_name} already exists; credentials retained"
  exit 0
fi

command -v openssl >/dev/null || {
  echo "openssl is required to generate the Grafana password" >&2
  exit 1
}

password="$(openssl rand -base64 32)"
trap 'unset password' EXIT INT TERM
kubectl -n "$namespace" create secret generic "$secret_name" \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="$password"
echo "created ${namespace}/${secret_name} (password redacted)"
