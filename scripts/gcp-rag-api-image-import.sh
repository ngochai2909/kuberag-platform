#!/usr/bin/env bash
# Import the local RAG API image into the single-node GCP k3s containerd store.
set -euo pipefail

ssh_target="${GCP_SSH_TARGET:-kuberag-gcp}"
image="${RAG_API_IMAGE:-kuberag-rag-api:local}"

echo "saving ${image} and importing on ${ssh_target} (may take several minutes over IAP)"
docker save "$image" | gzip -1 | ssh \
  -o BatchMode=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=6 \
  "$ssh_target" \
  'gzip -d | sudo k3s ctr images import -'

echo "imported image inventory (filtered):"
ssh -o BatchMode=yes "$ssh_target" \
  "sudo k3s ctr images ls | awk 'NR==1 || /kuberag-rag-api/'"
