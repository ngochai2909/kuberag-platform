# SEC-004 — Trivy image scan result

In CI run #31, the release-images job completed **Scan pushed images and
produce CycloneDX SBOMs** with `success` after API, ingestion and frontend had
been pushed by digest. The workflow invokes `trivy image` for each immutable
reference with `--severity HIGH,CRITICAL --ignore-unfixed --exit-code 1`.

Run: <https://github.com/ngochai2909/kuberag-platform/actions/runs/30798179207>

