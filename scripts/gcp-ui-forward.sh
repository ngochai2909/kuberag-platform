#!/usr/bin/env bash
# Open a local port-forward to Grafana or Prefect UI.
# Starts the IAP Kubernetes API tunnel in the background when needed.
set -euo pipefail

usage() {
  echo "Usage: $0 <grafana|prefect>" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage

target="$1"
kubeconfig="${KUBECONFIG:-${GCP_KUBECONFIG:-$HOME/.kube/kuberag-gcp.yaml}}"
ssh_target="${GCP_SSH_TARGET:-kuberag-gcp}"
tunnel_port="${GCP_K3S_TUNNEL_PORT:-16443}"
export KUBECONFIG="$kubeconfig"

ensure_tunnel() {
  if ss -ltn 2>/dev/null | grep -q ":${tunnel_port} "; then
    return 0
  fi
  echo "Starting Kubernetes API tunnel on 127.0.0.1:${tunnel_port} ..."
  ssh -f -N -o ExitOnForwardFailure=yes \
    -L "${tunnel_port}:127.0.0.1:6443" \
    "$ssh_target"
  for _ in $(seq 1 30); do
    if ss -ltn 2>/dev/null | grep -q ":${tunnel_port} "; then
      echo "Tunnel ready."
      return 0
    fi
    sleep 1
  done
  echo "Tunnel did not become ready on port ${tunnel_port}." >&2
  exit 1
}

ensure_tunnel

case "$target" in
  grafana)
    echo "Grafana -> http://127.0.0.1:3000"
    echo "Keep this terminal open. Ctrl+C stops the forward (tunnel may stay up)."
    exec kubectl -n observability port-forward service/kuberag-monitoring-grafana 3000:80
    ;;
  prefect)
    echo "Prefect UI -> http://127.0.0.1:4200"
    echo "Keep this terminal open. Ctrl+C stops the forward (tunnel may stay up)."
    exec kubectl -n prefect port-forward service/prefect-server 4200:4200
    ;;
  *)
    usage
    ;;
esac
