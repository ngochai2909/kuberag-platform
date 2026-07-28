#!/usr/bin/env bash
# Import the local kuberag-ingestion image into the GCP k3s containerd store.
set -euo pipefail

SSH_TARGET="${GCP_SSH_TARGET:-kuberag-gcp}"
IMAGE="${INGESTION_IMAGE:-kuberag-ingestion:local}"

echo "saving ${IMAGE} and importing on ${SSH_TARGET} (may take several minutes over IAP)"
docker save "$IMAGE" | ssh -o BatchMode=yes "$SSH_TARGET" \
  'sudo k3s ctr images import -'

echo "imported image inventory (filtered):"
ssh -o BatchMode=yes "$SSH_TARGET" \
  "sudo k3s ctr images ls | awk 'NR==1 || /kuberag-ingestion/'"
