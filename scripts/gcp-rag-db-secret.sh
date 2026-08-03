#!/usr/bin/env bash
# Copy the CNPG application URI into the rag namespace without printing it.
set -euo pipefail

KUBECONFIG="${KUBECONFIG:-${GCP_KUBECONFIG:-$HOME/.kube/kuberag-gcp.yaml}}"
export KUBECONFIG

source_ns="${SOURCE_NS:-data}"
source_secret="${SOURCE_SECRET:-kuberag-pg-app}"
target_ns="${TARGET_NS:-rag}"
target_secret="${TARGET_SECRET:-kuberag-rag-db}"

uri_b64="$(kubectl -n "$source_ns" get secret/"$source_secret" -o jsonpath='{.data.uri}')"
if [[ -z "$uri_b64" ]]; then
  echo "missing ${source_ns}/${source_secret} .data.uri" >&2
  exit 1
fi

kubectl -n "$target_ns" create secret generic "$target_secret" \
  --from-literal=uri="$(printf '%s' "$uri_b64" | base64 --decode)" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "synced secret ${target_ns}/${target_secret} from ${source_ns}/${source_secret} (uri redacted)"
