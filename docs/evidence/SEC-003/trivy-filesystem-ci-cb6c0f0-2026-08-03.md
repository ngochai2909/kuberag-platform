# SEC-003 — Trivy filesystem/configuration/secret CI result

GitHub Actions CI run #31 security job completed **Trivy filesystem,
configuration, and secret scan** with `success`.

The workflow scans filesystem vulnerabilities, secrets and misconfiguration;
it fails on HIGH/CRITICAL findings and deliberately excludes only the
documented negative privileged-Pod fixture used to prove PSS admission.

Run: <https://github.com/ngochai2909/kuberag-platform/actions/runs/30798179207>

