#!/usr/bin/env bash
# Create only the Secret that holds the Slack incoming-webhook URL. The
# Alertmanager routing configuration is safe to track in Git and references
# this file through api_url_file.
set -euo pipefail

: "${SLACK_WEBHOOK_URL:?Set SLACK_WEBHOOK_URL in the current shell}"

[[ "$SLACK_WEBHOOK_URL" =~ ^https://hooks\.slack\.com/services/[A-Za-z0-9/_-]+$ ]] || {
  echo "SLACK_WEBHOOK_URL must be a Slack incoming-webhook URL" >&2
  exit 1
}

kubectl --namespace observability create secret generic kuberag-slack-webhook \
  --from-literal=api-url="$SLACK_WEBHOOK_URL" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Updated observability/kuberag-slack-webhook without printing its value."
