#!/usr/bin/env bash
# Create the API bearer token in-cluster. Never print or commit its value.
set -euo pipefail

KUBECONFIG="${KUBECONFIG:-${GCP_KUBECONFIG:-$HOME/.kube/kuberag-gcp.yaml}}"
export KUBECONFIG

namespace="${RAG_API_NAMESPACE:-rag}"
secret_name="${RAG_API_AUTH_SECRET:-kuberag-rag-api-auth}"

if kubectl -n "$namespace" get secret "$secret_name" >/dev/null 2>&1; then
  echo "secret ${namespace}/${secret_name} already exists; token retained"
  exit 0
fi

command -v openssl >/dev/null || {
  echo "openssl is required to generate the API token" >&2
  exit 1
}

token="$(openssl rand -hex 32)"
trap 'unset token' EXIT INT TERM
kubectl -n "$namespace" create secret generic "$secret_name" \
  --from-literal=api-key="$token"
echo "created ${namespace}/${secret_name} (token redacted)"
