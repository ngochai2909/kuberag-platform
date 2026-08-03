#!/usr/bin/env bash
# Import the local RAG API image into the single-node GCP k3s containerd store.
set -euo pipefail

ssh_target="${GCP_SSH_TARGET:-kuberag-gcp}"
image="${RAG_API_IMAGE:-kuberag-rag-api:local}"

archive="$(mktemp --suffix=.tar.zst)"
remote_archive="/tmp/${image//[:\/]/-}.tar.zst"

cleanup() {
  rm -f "$archive"
}
trap cleanup EXIT

echo "saving ${image} to a compressed archive"
docker save "$image" | zstd --force --threads=0 --fast=3 -o "$archive"

echo "uploading archive to ${ssh_target} with resume support"
rsync --archive --partial --append-verify --progress \
  -e 'ssh -o BatchMode=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=6' \
  "$archive" "${ssh_target}:${remote_archive}"

echo "importing ${image} into k3s containerd"
ssh \
  -o BatchMode=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=6 \
  "$ssh_target" \
  "zstd -dc '$remote_archive' | sudo k3s ctr images import - && rm -f '$remote_archive'"

echo "imported image inventory (filtered):"
ssh -o BatchMode=yes "$ssh_target" \
  "sudo k3s ctr images ls | awk 'NR==1 || /kuberag-rag-api/'"
