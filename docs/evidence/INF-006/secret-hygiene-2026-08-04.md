# INF-006 Secret hygiene — 2026-08-04

## git ls-files review (sensitive name patterns)
(no matching tracked paths)

## Explicitly ignored paths present locally (must stay untracked)
infra/terraform/terraform.tfvars -> untracked
infra/terraform/tfplan-cloud-nat -> untracked
.kube -> untracked

## Trivy filesystem secret scan (repo root, skip node_modules/.venv)
trivy not installed locally; checking make scan / CI evidence

## Result

- No kubeconfig, terraform state, private keys, or `.env` values are tracked in Git.
- Local operator files (`.env`, `terraform.tfvars`, kubeconfig under `$HOME/.kube`) remain outside Git.
- See also CI Trivy secret evidence under `docs/evidence/SEC-003/`.
