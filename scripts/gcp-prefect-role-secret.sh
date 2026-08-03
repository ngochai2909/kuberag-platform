#!/usr/bin/env bash
# Create the CNPG-managed Prefect role password without printing it.
set -euo pipefail

KUBECONFIG="${KUBECONFIG:-${GCP_KUBECONFIG:-$HOME/.kube/kuberag-gcp.yaml}}"
export KUBECONFIG

namespace="${PREFECT_DB_SOURCE_NAMESPACE:-data}"
secret_name="${PREFECT_DB_ROLE_SECRET:-prefect-db-auth}"

if kubectl -n "$namespace" get secret "$secret_name" >/dev/null 2>&1; then
  echo "secret ${namespace}/${secret_name} already exists; password retained"
  exit 0
fi

command -v openssl >/dev/null || {
  echo "openssl is required to generate the Prefect database password" >&2
  exit 1
}

temp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$temp_dir"
}
trap cleanup EXIT INT TERM
umask 077

printf 'prefect' >"$temp_dir/username"
openssl rand -hex 24 >"$temp_dir/password"

kubectl -n "$namespace" create secret generic "$secret_name" \
  --type=kubernetes.io/basic-auth \
  --from-file=username="$temp_dir/username" \
  --from-file=password="$temp_dir/password" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "created ${namespace}/${secret_name} for CNPG DatabaseRole/prefect (password redacted)"
