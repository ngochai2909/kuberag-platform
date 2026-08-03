#!/bin/sh
set -eu

if [ "$#" -eq 0 ]; then
  echo "usage: scripts/gcp-db-run.sh COMMAND [ARG ...]" >&2
  exit 2
fi

SSH_TARGET="${GCP_SSH_TARGET:-kuberag-gcp}"
LOCAL_PORT="${GCP_DB_LOCAL_PORT:-15432}"

service_ip="$(
  ssh -o BatchMode=yes "$SSH_TARGET" \
    "sudo k3s kubectl -n data get service/kuberag-pg-rw \
      -o jsonpath='{.spec.clusterIP}'"
)"

ssh -o BatchMode=yes -N \
  -L "127.0.0.1:${LOCAL_PORT}:${service_ip}:5432" \
  "$SSH_TARGET" &
tunnel_pid=$!

cleanup() {
  kill "$tunnel_pid" 2>/dev/null || true
  wait "$tunnel_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

python3 - "$LOCAL_PORT" <<'PY'
import socket
import sys
import time

port = int(sys.argv[1])
for _ in range(30):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            break
    except OSError:
        time.sleep(1)
else:
    raise SystemExit("database SSH tunnel did not become ready")
PY

raw_database_url="$(
  ssh -o BatchMode=yes "$SSH_TARGET" \
    "sudo k3s kubectl -n data get secret/kuberag-pg-app \
      -o jsonpath='{.data.uri}'" |
    base64 --decode
)"

DATABASE_URL="$(
  RAW_DATABASE_URL="$raw_database_url" python3 - "$LOCAL_PORT" <<'PY'
import os
import sys
from urllib.parse import urlsplit, urlunsplit

raw_url = os.environ["RAW_DATABASE_URL"]
port = int(sys.argv[1])
parts = urlsplit(raw_url)
if parts.username is None or parts.password is None:
    raise SystemExit("generated database URI is missing credentials")
userinfo = f"{parts.username}:{parts.password}"
print(urlunsplit((parts.scheme, f"{userinfo}@127.0.0.1:{port}", parts.path, parts.query, "")))
PY
)"
unset raw_database_url
export DATABASE_URL

"$@"
