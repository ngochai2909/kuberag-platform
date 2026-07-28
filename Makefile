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

.PHONY: setup run test test-cov lint format format-check typecheck check lock clean infra-check k3s-install gcp-k3s-syntax gcp-k3s-install gcp-k3s-tunnel gcp-k3s-status gcp-envoy-install gcp-foundation-apply gcp-foundation-delete gcp-foundation-status gcp-foundation-smoke gcp-unsafe-check k3s-foundation-apply k3s-foundation-delete k3s-foundation-status k3s-foundation-smoke k3s-unsafe-check cnpg-render postgresql-render gcp-cnpg-install gcp-postgresql-apply gcp-postgresql-status

setup:
	uv sync --group dev

run:
	uv run uvicorn app.main:app --reload --host $${APP_HOST:-0.0.0.0} --port $${APP_PORT:-8000}

test:
	uv run pytest

test-cov:
	uv run pytest --cov-report=html

lint:
	uv run ruff check apps/rag-api/src apps/rag-api/tests

format:
	uv run ruff format apps/rag-api/src apps/rag-api/tests

format-check:
	uv run ruff format --check apps/rag-api/src apps/rag-api/tests

typecheck:
	uv run mypy apps/rag-api/src apps/rag-api/tests

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

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .mypy_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +
	find . -type f -name .coverage -delete
