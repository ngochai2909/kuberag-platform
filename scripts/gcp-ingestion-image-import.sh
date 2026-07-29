#!/usr/bin/env bash
# Import the local kuberag-ingestion image into the GCP k3s containerd store.
set -euo pipefail

SSH_TARGET="${GCP_SSH_TARGET:-kuberag-gcp}"
IMAGE="${INGESTION_IMAGE:-kuberag-ingestion:local}"

echo "saving ${IMAGE} and importing on ${SSH_TARGET} (may take several minutes over IAP)"
# Compression substantially reduces the long IAP stream for the Torch CPU image.
docker save "$IMAGE" | gzip -1 | ssh \
  -o BatchMode=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=6 \
  "$SSH_TARGET" \
  'gzip -d | sudo k3s ctr images import -'

echo "imported image inventory (filtered):"
ssh -o BatchMode=yes "$SSH_TARGET" \
  "sudo k3s ctr images ls | awk 'NR==1 || /kuberag-ingestion/'"
