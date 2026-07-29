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
INGESTION_IMAGE ?= kuberag-ingestion:local
UV_VERSION ?= 0.11.15
PREFECT_DB_SECRET_SCRIPT ?= scripts/gcp-prefect-db-secret.sh
PREFECT_ROLE_SECRET_SCRIPT ?= scripts/gcp-prefect-role-secret.sh
PREFECT_SERVER_DB_SECRET_SCRIPT ?= scripts/gcp-prefect-server-db-secret.sh
INGESTION_IMAGE_IMPORT_SCRIPT ?= scripts/gcp-ingestion-image-import.sh

.PHONY: setup run test test-cov lint format format-check typecheck check lock clean infra-check k3s-install gcp-k3s-syntax gcp-k3s-install gcp-k3s-tunnel gcp-k3s-status gcp-envoy-install gcp-foundation-apply gcp-foundation-delete gcp-foundation-status gcp-foundation-smoke gcp-unsafe-check k3s-foundation-apply k3s-foundation-delete k3s-foundation-status k3s-foundation-smoke k3s-unsafe-check cnpg-render postgresql-render migration-sql gcp-cnpg-install gcp-postgresql-apply gcp-postgresql-status gcp-db-migrate gcp-db-current gcp-db-vector-test gcp-rag-retrieval-test docker-ingestion-build docker-ingestion-smoke gcp-ingestion-image-import gcp-prefect-db-secret gcp-prefect-role-secret gcp-prefect-server-db-secret gcp-prefect-apply gcp-prefect-bootstrap gcp-prefect-worker-apply gcp-prefect-worker-restart gcp-prefect-status gcp-e5-download gcp-e5-smoke gcp-ingest-run

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

check: lint format-check typecheck test

lock:
	uv lock

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
