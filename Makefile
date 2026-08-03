KUBECONFIG ?= $(HOME)/.kube/kuberag-k3s.yaml
KUSTOMIZE_LOCAL ?= deploy/kustomize/overlays/local
GCP_ANSIBLE_INVENTORY ?= infra/ansible/inventory/gcp.ini
GCP_KUBECONFIG ?= $(HOME)/.kube/kuberag-gcp.yaml
GCP_KUSTOMIZE ?= deploy/kustomize/overlays/gcp
ENVOY_GATEWAY_VERSION ?= v1.8.3
CNPG_CHART_VERSION ?= 0.29.0
CNPG_CHART ?= oci://ghcr.io/cloudnative-pg/charts/cloudnative-pg
CNPG_VALUES ?= deploy/helm/cloudnative-pg/values.yaml
POSTGRES_BASE_KUSTOMIZE ?= deploy/kustomize/base/postgresql
POSTGRES_LOCAL_KUSTOMIZE ?= deploy/kustomize/overlays/local/postgresql
POSTGRES_GCP_KUSTOMIZE ?= deploy/kustomize/overlays/gcp/postgresql
PREFECT_GCP_KUSTOMIZE ?= deploy/kustomize/overlays/gcp/prefect
PREFECT_WORKER_GCP_KUSTOMIZE ?= deploy/kustomize/overlays/gcp/prefect-worker
PREFECT_BOOTSTRAP_JOB ?= deploy/kustomize/base/prefect/bootstrap-job.yaml
E5_DOWNLOAD_JOB ?= deploy/kustomize/base/prefect/e5-download-job.yaml
E5_SMOKE_JOB ?= deploy/kustomize/base/prefect/e5-smoke-job.yaml
INGEST_RUN_JOB ?= deploy/kustomize/base/prefect/ingest-run-job.yaml
ALEMBIC_CONFIG ?= apps/ingestion/alembic.ini
DB_RUN_SCRIPT ?= scripts/gcp-db-run.sh
DB_INTEGRATION_TEST ?= apps/ingestion/tests/integration/test_vector_query.py
RAG_RETRIEVAL_INTEGRATION_TEST ?= apps/rag-api/tests/integration/test_postgres_retriever.py
LLAMA_GCP_KUSTOMIZE ?= deploy/kustomize/overlays/gcp/llama-cpp
RAG_API_GCP_KUSTOMIZE ?= deploy/kustomize/overlays/gcp/rag-api
FRONTEND_GCP_KUSTOMIZE ?= deploy/kustomize/overlays/gcp/frontend
RAG_ROUTING_GCP_KUSTOMIZE ?= deploy/kustomize/overlays/gcp/rag-routing
RAG_RATE_LIMIT_BURST ?= 11
INGESTION_IMAGE ?= kuberag-ingestion:local
RAG_API_IMAGE ?= kuberag-rag-api:local
FRONTEND_IMAGE ?= kuberag-web:local
UV_VERSION ?= 0.11.15
PREFECT_DB_SECRET_SCRIPT ?= scripts/gcp-prefect-db-secret.sh
PREFECT_ROLE_SECRET_SCRIPT ?= scripts/gcp-prefect-role-secret.sh
PREFECT_SERVER_DB_SECRET_SCRIPT ?= scripts/gcp-prefect-server-db-secret.sh
RAG_DB_SECRET_SCRIPT ?= scripts/gcp-rag-db-secret.sh
RAG_API_AUTH_SECRET_SCRIPT ?= scripts/gcp-rag-api-auth-secret.sh
INGESTION_IMAGE_IMPORT_SCRIPT ?= scripts/gcp-ingestion-image-import.sh
RAG_API_IMAGE_IMPORT_SCRIPT ?= scripts/gcp-rag-api-image-import.sh
FRONTEND_IMAGE_IMPORT_SCRIPT ?= scripts/gcp-frontend-image-import.sh
FRONTEND_DIR ?= apps/frontend
OBSERVABILITY_NAMESPACE ?= observability
OBSERVABILITY_VALUES_DIR ?= deploy/helm/observability
OBSERVABILITY_KUSTOMIZE ?= observability
KUBE_PROMETHEUS_STACK_VERSION ?= 87.21.0
LOKI_CHART_VERSION ?= 7.2.0
TEMPO_CHART_VERSION ?= 1.24.4
PYROSCOPE_CHART_VERSION ?= 2.2.0
OTEL_COLLECTOR_CHART_VERSION ?= 0.165.0
GRAFANA_ADMIN_SECRET_SCRIPT ?= scripts/gcp-grafana-admin-secret.sh
ALERTMANAGER_SLACK_SECRET_SCRIPT ?= scripts/gcp-alertmanager-slack-secret.sh
K6_GATEWAY_URL ?=
K6_SUMMARY_DIR ?= docs/evidence/PERF-001

.PHONY: setup run test test-cov lint format format-check typecheck check lock clean frontend-install frontend-dev frontend-typecheck frontend-build docker-frontend-build gcp-frontend-image-import gcp-frontend-render gcp-frontend-apply gcp-frontend-status gcp-frontend-smoke infra-check k3s-install gcp-k3s-syntax gcp-k3s-install gcp-k3s-tunnel gcp-k3s-status gcp-envoy-install gcp-foundation-apply gcp-foundation-delete gcp-foundation-status gcp-foundation-smoke gcp-unsafe-check k3s-foundation-apply k3s-foundation-delete k3s-foundation-status k3s-foundation-smoke k3s-unsafe-check cnpg-render postgresql-render migration-sql gcp-cnpg-install gcp-postgresql-apply gcp-postgresql-status gcp-db-migrate gcp-db-current gcp-db-vector-test gcp-rag-retrieval-test gcp-llama-render gcp-llama-apply gcp-llama-status docker-ingestion-build docker-ingestion-smoke gcp-ingestion-image-import docker-rag-api-build docker-rag-api-smoke gcp-rag-api-image-import gcp-rag-db-secret gcp-rag-api-auth-secret gcp-rag-api-render gcp-rag-api-apply gcp-rag-api-status gcp-rag-routing-render gcp-rag-routing-apply gcp-rag-routing-status gcp-rag-routing-smoke gcp-rag-rate-limit-smoke gcp-prefect-db-secret gcp-prefect-role-secret gcp-prefect-server-db-secret gcp-prefect-apply gcp-prefect-bootstrap gcp-prefect-worker-apply gcp-prefect-worker-restart gcp-prefect-status gcp-e5-download gcp-e5-smoke gcp-ingest-run
.PHONY: gcp-grafana-admin-secret gcp-alertmanager-slack-secret gcp-observability-render gcp-observability-install gcp-observability-apply gcp-observability-status gcp-observability-grafana-port-forward gcp-alert-lifecycle-test gcp-alert-lifecycle-cleanup k6-load k6-rate-limit

setup:
	uv sync --group dev

run:
	uv run uvicorn app.main:app --reload --host $${APP_HOST:-0.0.0.0} --port $${APP_PORT:-8000}

test:
	uv run pytest

test-cov:
	uv run pytest --cov-report=html

lint:
	uv run ruff check apps/rag-api/src apps/rag-api/tests apps/ingestion/src apps/ingestion/tests

format:
	uv run ruff format apps/rag-api/src apps/rag-api/tests apps/ingestion/src apps/ingestion/tests

format-check:
	uv run ruff format --check apps/rag-api/src apps/rag-api/tests apps/ingestion/src apps/ingestion/tests

typecheck:
	uv run mypy apps/rag-api/src apps/rag-api/tests apps/ingestion/src apps/ingestion/tests

check: lint format-check typecheck test frontend-typecheck frontend-build

lock:
	uv lock

frontend-install:
	npm --prefix $(FRONTEND_DIR) install

frontend-dev:
	npm --prefix $(FRONTEND_DIR) run dev -- --host 127.0.0.1

frontend-typecheck:
	npm --prefix $(FRONTEND_DIR) run typecheck

frontend-build:
	npm --prefix $(FRONTEND_DIR) run build

docker-frontend-build:
	docker build \
		-f apps/frontend/Dockerfile \
		-t $(FRONTEND_IMAGE) \
		.

gcp-frontend-image-import: docker-frontend-build
	FRONTEND_IMAGE=$(FRONTEND_IMAGE) $(FRONTEND_IMAGE_IMPORT_SCRIPT)

gcp-frontend-render:
	kubectl kustomize $(FRONTEND_GCP_KUSTOMIZE)

gcp-frontend-apply:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(FRONTEND_GCP_KUSTOMIZE)
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag wait --for=condition=Available deployment/kuberag-web --timeout=300s

gcp-frontend-status:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get deployment/kuberag-web service/kuberag-web
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get pods -l app.kubernetes.io/name=kuberag-web -o wide

gcp-frontend-smoke:
	@gateway_address=$$(terraform -chdir=infra/terraform output -raw external_ip); \
	curl --fail --silent --show-error "http://$$gateway_address:8080/" | grep -q '<title>KubeRAG</title>'

infra-check:
	@command -v terraform >/dev/null || (echo "terraform is required" && exit 1)
	@command -v ansible-playbook >/dev/null || (echo "ansible-playbook is required" && exit 1)

k3s-install:
	ansible-playbook -i infra/ansible/inventory/local.ini infra/ansible/playbooks/k3s-single-node.yml --ask-become-pass

gcp-k3s-syntax:
	ansible-playbook -i $(GCP_ANSIBLE_INVENTORY) infra/ansible/playbooks/k3s-gcp-single-node.yml --syntax-check

gcp-k3s-install:
	ansible-playbook -i $(GCP_ANSIBLE_INVENTORY) infra/ansible/playbooks/k3s-gcp-single-node.yml

gcp-k3s-tunnel:
	ssh -N -L 16443:127.0.0.1:6443 kuberag-gcp

gcp-k3s-status:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl get nodes -o wide

gcp-grafana-admin-secret:
	KUBECONFIG=$(GCP_KUBECONFIG) $(GRAFANA_ADMIN_SECRET_SCRIPT)

gcp-alertmanager-slack-secret:
	KUBECONFIG=$(GCP_KUBECONFIG) bash $(ALERTMANAGER_SLACK_SECRET_SCRIPT)

gcp-observability-render:
	helm template kuberag-monitoring prometheus-community/kube-prometheus-stack \
		--version $(KUBE_PROMETHEUS_STACK_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--values $(OBSERVABILITY_VALUES_DIR)/kube-prometheus-stack-values.yaml
	helm template kuberag-loki grafana/loki \
		--version $(LOKI_CHART_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--values $(OBSERVABILITY_VALUES_DIR)/loki-values.yaml
	helm template kuberag-tempo grafana/tempo \
		--version $(TEMPO_CHART_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--values $(OBSERVABILITY_VALUES_DIR)/tempo-values.yaml
	helm template kuberag-pyroscope grafana/pyroscope \
		--version $(PYROSCOPE_CHART_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--values $(OBSERVABILITY_VALUES_DIR)/pyroscope-values.yaml
	helm template kuberag-otel open-telemetry/opentelemetry-collector \
		--version $(OTEL_COLLECTOR_CHART_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--values $(OBSERVABILITY_VALUES_DIR)/otel-collector-values.yaml
	kubectl kustomize $(OBSERVABILITY_KUSTOMIZE)

gcp-observability-install: gcp-grafana-admin-secret
	KUBECONFIG=$(GCP_KUBECONFIG) helm upgrade --install kuberag-monitoring prometheus-community/kube-prometheus-stack \
		--version $(KUBE_PROMETHEUS_STACK_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--create-namespace \
		--values $(OBSERVABILITY_VALUES_DIR)/kube-prometheus-stack-values.yaml
	KUBECONFIG=$(GCP_KUBECONFIG) helm upgrade --install kuberag-loki grafana/loki \
		--version $(LOKI_CHART_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--create-namespace \
		--values $(OBSERVABILITY_VALUES_DIR)/loki-values.yaml
	KUBECONFIG=$(GCP_KUBECONFIG) helm upgrade --install kuberag-tempo grafana/tempo \
		--version $(TEMPO_CHART_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--create-namespace \
		--values $(OBSERVABILITY_VALUES_DIR)/tempo-values.yaml
	KUBECONFIG=$(GCP_KUBECONFIG) helm upgrade --install kuberag-pyroscope grafana/pyroscope \
		--version $(PYROSCOPE_CHART_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--create-namespace \
		--values $(OBSERVABILITY_VALUES_DIR)/pyroscope-values.yaml
	KUBECONFIG=$(GCP_KUBECONFIG) helm upgrade --install kuberag-otel open-telemetry/opentelemetry-collector \
		--version $(OTEL_COLLECTOR_CHART_VERSION) \
		--namespace $(OBSERVABILITY_NAMESPACE) \
		--create-namespace \
		--values $(OBSERVABILITY_VALUES_DIR)/otel-collector-values.yaml
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n $(OBSERVABILITY_NAMESPACE) wait --for=condition=Available deployment/kuberag-monitoring-grafana --timeout=10m
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n $(OBSERVABILITY_NAMESPACE) wait --for=condition=Available deployment/kuberag-otel-collector --timeout=10m
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n $(OBSERVABILITY_NAMESPACE) rollout status statefulset/kuberag-loki --timeout=10m
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n $(OBSERVABILITY_NAMESPACE) rollout status statefulset/kuberag-tempo --timeout=10m
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n $(OBSERVABILITY_NAMESPACE) rollout status statefulset/kuberag-pyroscope --timeout=10m

gcp-observability-apply:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(OBSERVABILITY_KUSTOMIZE)

gcp-observability-status:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n $(OBSERVABILITY_NAMESPACE) get deployment,statefulset,pods,services,pvc -o wide
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl get servicemonitor -A
	KUBECONFIG=$(GCP_KUBECONFIG) helm list -n $(OBSERVABILITY_NAMESPACE)

gcp-observability-grafana-port-forward:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n $(OBSERVABILITY_NAMESPACE) port-forward service/kuberag-monitoring-grafana 3000:80

gcp-alert-lifecycle-test:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -f observability/alerts/test-lifecycle.yaml

gcp-alert-lifecycle-cleanup:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl delete -f observability/alerts/test-lifecycle.yaml

k6-load:
	@test -n "$(K6_GATEWAY_URL)" || (echo "Set K6_GATEWAY_URL=http://VM_EXTERNAL_IP:8080" && exit 1)
	@mkdir -p $(K6_SUMMARY_DIR)
	KUBERAG_GATEWAY_URL=$(K6_GATEWAY_URL) k6 run --summary-export=$(K6_SUMMARY_DIR)/load-summary.json tests/k6/load.js

k6-rate-limit:
	@test -n "$(K6_GATEWAY_URL)" || (echo "Set K6_GATEWAY_URL=http://VM_EXTERNAL_IP:8080" && exit 1)
	@mkdir -p $(K6_SUMMARY_DIR)
	KUBERAG_GATEWAY_URL=$(K6_GATEWAY_URL) k6 run --summary-export=$(K6_SUMMARY_DIR)/rate-limit-summary.json tests/k6/rate-limit.js

gcp-envoy-install:
	KUBECONFIG=$(GCP_KUBECONFIG) helm upgrade --install envoy-gateway \
		oci://docker.io/envoyproxy/gateway-helm \
		--version $(ENVOY_GATEWAY_VERSION) \
		--namespace gateway-system \
		--create-namespace
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl wait --timeout=5m --namespace gateway-system \
		deployment/envoy-gateway --for=condition=Available

cnpg-render:
	helm template cloudnative-pg $(CNPG_CHART) \
		--version $(CNPG_CHART_VERSION) \
		--namespace data \
		--values $(CNPG_VALUES)

postgresql-render:
	kubectl kustomize $(POSTGRES_BASE_KUSTOMIZE)
	kubectl kustomize $(POSTGRES_LOCAL_KUSTOMIZE)
	kubectl kustomize $(POSTGRES_GCP_KUSTOMIZE)

migration-sql:
	DATABASE_URL=postgresql://kuberag:placeholder@localhost:5432/kuberag \
		uv run alembic -c $(ALEMBIC_CONFIG) upgrade head --sql

gcp-cnpg-install:
	KUBECONFIG=$(GCP_KUBECONFIG) helm upgrade --install cloudnative-pg \
		$(CNPG_CHART) \
		--version $(CNPG_CHART_VERSION) \
		--namespace data \
		--create-namespace \
		--values $(CNPG_VALUES)
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl wait --timeout=5m --namespace data \
		deployment/cloudnative-pg --for=condition=Available

gcp-postgresql-apply:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(POSTGRES_GCP_KUSTOMIZE)

gcp-postgresql-status:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl --namespace data get deployment/cloudnative-pg
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl --namespace data get cluster/kuberag-pg
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl --namespace data get database/kuberag
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl --namespace data get pods,services,pvc -o wide
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl --namespace data get secret/kuberag-pg-app

gcp-db-migrate:
	$(DB_RUN_SCRIPT) uv run alembic -c $(ALEMBIC_CONFIG) upgrade head

gcp-db-current:
	$(DB_RUN_SCRIPT) uv run alembic -c $(ALEMBIC_CONFIG) current

gcp-db-vector-test:
	$(DB_RUN_SCRIPT) uv run pytest --no-cov -q -m db_integration $(DB_INTEGRATION_TEST)

gcp-rag-retrieval-test:
	$(DB_RUN_SCRIPT) uv run pytest --no-cov -q -m db_integration $(RAG_RETRIEVAL_INTEGRATION_TEST)

gcp-llama-render:
	kubectl kustomize $(LLAMA_GCP_KUSTOMIZE)

gcp-llama-apply:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(LLAMA_GCP_KUSTOMIZE)

gcp-llama-status:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get deployment/kuberag-llm service/kuberag-llm pvc/kuberag-llm-models
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get pods -l app.kubernetes.io/name=kuberag-llm -o wide

docker-rag-api-build:
	docker build \
		--build-arg UV_VERSION=$(UV_VERSION) \
		-f apps/rag-api/Dockerfile \
		-t $(RAG_API_IMAGE) \
		.

docker-rag-api-smoke: docker-rag-api-build
	docker run --rm $(RAG_API_IMAGE) /app/.venv/bin/python -c "from app.main import app; print(app.title)"

gcp-rag-api-image-import: docker-rag-api-build
	RAG_API_IMAGE=$(RAG_API_IMAGE) $(RAG_API_IMAGE_IMPORT_SCRIPT)

gcp-rag-db-secret:
	KUBECONFIG=$(GCP_KUBECONFIG) $(RAG_DB_SECRET_SCRIPT)

gcp-rag-api-auth-secret:
	KUBECONFIG=$(GCP_KUBECONFIG) $(RAG_API_AUTH_SECRET_SCRIPT)

gcp-rag-api-render:
	kubectl kustomize $(RAG_API_GCP_KUSTOMIZE)

gcp-rag-api-apply:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(RAG_API_GCP_KUSTOMIZE)

gcp-rag-api-status:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get deployment/kuberag-rag-api service/kuberag-rag-api pvc/kuberag-rag-embedding-models
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get pods -l app.kubernetes.io/name=kuberag-rag-api -o wide

gcp-rag-routing-render:
	kubectl kustomize $(RAG_ROUTING_GCP_KUSTOMIZE)

gcp-rag-routing-apply:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(RAG_ROUTING_GCP_KUSTOMIZE)

gcp-rag-routing-status:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get gateway/kuberag httproute/kuberag-api backendtrafficpolicy/kuberag-api-rate-limit -o wide

gcp-rag-routing-smoke:
	@test "$$(KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get httproute/kuberag-api -o jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}')" = "True"
	@test "$$(KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get httproute/kuberag-api -o jsonpath='{.status.parents[0].conditions[?(@.type=="ResolvedRefs")].status}')" = "True"
	@gateway_address=$$(terraform -chdir=infra/terraform output -raw external_ip); \
		curl --fail --silent --show-error "http://$$gateway_address:8080/api/v1/query" \
			-H 'Content-Type: application/json' \
			-d '{"question":"Nguon tin nay den tu dau?","top_k":2}' | jq -e '.answer and (.sources | length > 0) and .request_id and .trace_id' >/dev/null

gcp-rag-rate-limit-smoke:
	@gateway_address=$$(terraform -chdir=infra/terraform output -raw external_ip); \
		statuses=$$(for request in $$(seq 1 $(RAG_RATE_LIMIT_BURST)); do \
			curl --silent --output /dev/null --write-out '%{http_code}\n' \
				--connect-timeout 10 --max-time 15 \
				"http://$$gateway_address:8080/api/v1/query" \
				-H 'Content-Type: application/json' \
				-d '{"question":"rate limit verification","top_k":2}'; \
		done); \
		printf '%s\n' "$$statuses"; \
		test "$$(printf '%s\n' "$$statuses" | grep -c '^429$$')" -ge 1

gcp-foundation-apply:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(GCP_KUSTOMIZE)

gcp-foundation-delete:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl delete -k $(GCP_KUSTOMIZE)

gcp-foundation-status:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl get nodes -o wide
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl get namespaces rag data prefect loadtest observability gateway-system --show-labels
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n gateway-system get deployment/envoy-gateway
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl get gatewayclass kuberag
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get deployment,pods,services,gateway,httproute -o wide
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n gateway-system get pods,services -l gateway.envoyproxy.io/owning-gateway-name=kuberag -o wide

gcp-foundation-smoke:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag wait --for=condition=Available deployment/kuberag-pss-smoke --timeout=120s
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag wait --for=condition=Programmed gateway/kuberag --timeout=120s
	@test "$$(KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get httproute/kuberag-smoke -o jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}')" = "True"
	@test "$$(KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag get httproute/kuberag-smoke -o jsonpath='{.status.parents[0].conditions[?(@.type=="ResolvedRefs")].status}')" = "True"
	@gateway_address=$$(terraform -chdir=infra/terraform output -raw external_ip); \
		test -n "$$gateway_address"; \
		curl --fail --silent --show-error "http://$$gateway_address:8080/hostname"

gcp-unsafe-check:
	@if KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -f deploy/kustomize/examples/unsafe-root-pod.yaml; then \
		echo "unsafe manifest was accepted; PSS restricted is not enforced"; \
		KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n rag delete pod kuberag-unsafe-root --ignore-not-found; \
		exit 1; \
	else \
		echo "unsafe manifest rejected as expected"; \
	fi

k3s-foundation-apply:
	KUBECONFIG=$(KUBECONFIG) kubectl apply -k $(KUSTOMIZE_LOCAL)

k3s-foundation-delete:
	KUBECONFIG=$(KUBECONFIG) kubectl delete -k $(KUSTOMIZE_LOCAL)

k3s-foundation-status:
	KUBECONFIG=$(KUBECONFIG) kubectl get nodes -o wide
	KUBECONFIG=$(KUBECONFIG) kubectl get namespaces rag data prefect loadtest observability gateway-system -o yaml
	KUBECONFIG=$(KUBECONFIG) kubectl -n rag get pods,svc -o wide
	KUBECONFIG=$(KUBECONFIG) kubectl get gatewayclass kuberag
	KUBECONFIG=$(KUBECONFIG) kubectl -n rag get gateway,httproute
	KUBECONFIG=$(KUBECONFIG) kubectl -n gateway-system get pods,svc -l gateway.envoyproxy.io/owning-gateway-name=kuberag -o wide

k3s-foundation-smoke:
	KUBECONFIG=$(KUBECONFIG) kubectl -n rag wait --for=condition=Available deployment/kuberag-pss-smoke --timeout=120s
	KUBECONFIG=$(KUBECONFIG) kubectl -n rag wait --for=condition=Programmed gateway/kuberag --timeout=120s
	@test "$$(KUBECONFIG=$(KUBECONFIG) kubectl -n rag get httproute/kuberag-smoke -o jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}')" = "True"
	@test "$$(KUBECONFIG=$(KUBECONFIG) kubectl -n rag get httproute/kuberag-smoke -o jsonpath='{.status.parents[0].conditions[?(@.type=="ResolvedRefs")].status}')" = "True"
	@gateway_address=$$(KUBECONFIG=$(KUBECONFIG) kubectl -n rag get gateway/kuberag -o jsonpath='{.status.addresses[0].value}'); \
		test -n "$$gateway_address"; \
		curl --fail --silent --show-error "http://$$gateway_address:8080/hostname"

k3s-unsafe-check:
	@if KUBECONFIG=$(KUBECONFIG) kubectl apply -f deploy/kustomize/examples/unsafe-root-pod.yaml; then \
		echo "unsafe manifest was accepted; PSS restricted is not enforced"; \
		KUBECONFIG=$(KUBECONFIG) kubectl -n rag delete pod kuberag-unsafe-root --ignore-not-found; \
		exit 1; \
	else \
		echo "unsafe manifest rejected as expected"; \
	fi

docker-ingestion-build:
	docker build \
		--build-arg UV_VERSION=$(UV_VERSION) \
		-f apps/ingestion/Dockerfile \
		-t $(INGESTION_IMAGE) \
		.

docker-ingestion-smoke: docker-ingestion-build
	docker run --rm $(INGESTION_IMAGE)

gcp-ingestion-image-import: docker-ingestion-build
	INGESTION_IMAGE=$(INGESTION_IMAGE) $(INGESTION_IMAGE_IMPORT_SCRIPT)

gcp-prefect-db-secret:
	KUBECONFIG=$(GCP_KUBECONFIG) $(PREFECT_DB_SECRET_SCRIPT)

gcp-prefect-role-secret:
	KUBECONFIG=$(GCP_KUBECONFIG) $(PREFECT_ROLE_SECRET_SCRIPT)

gcp-prefect-server-db-secret:
	KUBECONFIG=$(GCP_KUBECONFIG) $(PREFECT_SERVER_DB_SECRET_SCRIPT)

gcp-prefect-apply:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(PREFECT_GCP_KUSTOMIZE)
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect wait --for=condition=Available deployment/prefect-server --timeout=300s

gcp-prefect-bootstrap:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect delete job/prefect-bootstrap --ignore-not-found
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -f $(PREFECT_BOOTSTRAP_JOB)
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect wait --for=condition=Complete job/prefect-bootstrap --timeout=300s
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect logs job/prefect-bootstrap

gcp-prefect-worker-apply:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(PREFECT_WORKER_GCP_KUSTOMIZE)
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect wait --for=condition=Available deployment/prefect-worker --timeout=300s

gcp-prefect-worker-restart:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect rollout restart deployment/prefect-worker
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect rollout status deployment/prefect-worker --timeout=300s

gcp-prefect-status:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect get deploy,pods,svc,pvc,job,secret -o wide
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect get deploy/prefect-server -o jsonpath='{.status.availableReplicas}{" server-available\n"}'
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect get deploy/prefect-worker -o jsonpath='{.status.availableReplicas}{" worker-available\n"}'

gcp-e5-download:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -k $(PREFECT_GCP_KUSTOMIZE)
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect delete job/kuberag-e5-download --ignore-not-found
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -f $(E5_DOWNLOAD_JOB)
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect wait --for=condition=Complete job/kuberag-e5-download --timeout=900s
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect logs job/kuberag-e5-download

gcp-e5-smoke:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect delete job/kuberag-e5-smoke --ignore-not-found
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -f $(E5_SMOKE_JOB)
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect wait --for=condition=Complete job/kuberag-e5-smoke --timeout=300s
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect logs job/kuberag-e5-smoke

gcp-ingest-run:
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect delete job/kuberag-ingest-run --ignore-not-found
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl apply -f $(INGEST_RUN_JOB)
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect wait --for=condition=Complete job/kuberag-ingest-run --timeout=3600s
	KUBECONFIG=$(GCP_KUBECONFIG) kubectl -n prefect logs job/kuberag-ingest-run

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type f -name .coverage -delete
