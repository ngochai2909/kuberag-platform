KUBECONFIG ?= $(HOME)/.kube/kuberag-k3s.yaml
KUSTOMIZE_LOCAL ?= deploy/kustomize/overlays/local

.PHONY: setup run test test-cov lint format format-check typecheck check lock clean infra-check k3s-install k3s-foundation-apply k3s-foundation-delete k3s-foundation-status k3s-foundation-smoke k3s-unsafe-check

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
