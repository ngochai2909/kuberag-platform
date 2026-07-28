#!/usr/bin/env bash
# Copy the CloudNativePG app URI into namespace prefect for the worker.
# Does not print credential values.
set -euo pipefail

KUBECONFIG="${KUBECONFIG:-${GCP_KUBECONFIG:-$HOME/.kube/kuberag-gcp.yaml}}"
export KUBECONFIG

SOURCE_NS="${SOURCE_NS:-data}"
SOURCE_SECRET="${SOURCE_SECRET:-kuberag-pg-app}"
TARGET_NS="${TARGET_NS:-prefect}"
TARGET_SECRET="${TARGET_SECRET:-kuberag-db-app}"

uri_b64="$(kubectl -n "$SOURCE_NS" get secret/"$SOURCE_SECRET" -o jsonpath='{.data.uri}')"
if [[ -z "$uri_b64" ]]; then
  echo "missing ${SOURCE_NS}/${SOURCE_SECRET} .data.uri" >&2
  exit 1
fi

kubectl -n "$TARGET_NS" create secret generic "$TARGET_SECRET" \
  --from-literal=uri="$(printf '%s' "$uri_b64" | base64 --decode)" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "synced secret ${TARGET_NS}/${TARGET_SECRET} from ${SOURCE_NS}/${SOURCE_SECRET} (uri redacted)"
