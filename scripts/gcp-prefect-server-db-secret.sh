#!/usr/bin/env bash
# Publish a Prefect-specific asyncpg URI into the prefect namespace.
set -euo pipefail

KUBECONFIG="${KUBECONFIG:-${GCP_KUBECONFIG:-$HOME/.kube/kuberag-gcp.yaml}}"
export KUBECONFIG

source_namespace="${PREFECT_DB_SOURCE_NAMESPACE:-data}"
source_secret="${PREFECT_DB_ROLE_SECRET:-prefect-db-auth}"
target_namespace="${PREFECT_DB_TARGET_NAMESPACE:-prefect}"
target_secret="${PREFECT_SERVER_DB_SECRET:-prefect-server-db}"
database_host="${PREFECT_DB_HOST:-kuberag-pg-rw.data.svc.cluster.local}"
database_name="${PREFECT_DB_NAME:-prefect}"

temp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$temp_dir"
}
trap cleanup EXIT INT TERM
umask 077

kubectl -n "$source_namespace" get secret "$source_secret" \
  -o jsonpath='{.data.username}' | base64 --decode >"$temp_dir/username"
kubectl -n "$source_namespace" get secret "$source_secret" \
  -o jsonpath='{.data.password}' | base64 --decode >"$temp_dir/password"

username="$(<"$temp_dir/username")"
password="$(<"$temp_dir/password")"
if [[ -z "$username" || -z "$password" ]]; then
  echo "missing username or password in ${source_namespace}/${source_secret}" >&2
  exit 1
fi

printf 'postgresql+asyncpg://%s:%s@%s:5432/%s' \
  "$username" "$password" "$database_host" "$database_name" >"$temp_dir/uri"
unset username password

kubectl -n "$target_namespace" create secret generic "$target_secret" \
  --from-file=uri="$temp_dir/uri" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "synced ${target_namespace}/${target_secret} from ${source_namespace}/${source_secret} (URI redacted)"
