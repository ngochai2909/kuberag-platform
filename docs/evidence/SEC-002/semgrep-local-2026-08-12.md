# SEC-002 — Semgrep local scan (2026-08-12)

Lệnh chỉ-đọc đã chạy từ repository root:

```bash
UV_CACHE_DIR=/tmp/kuberag-uv-cache \
  uvx semgrep scan --config p/default --error apps deploy infra observability scripts
```

Kết quả thực tế:

```text
Scanning 248 files tracked by git with 1074 Code rules
Ran 623 rules on 248 files: 0 findings.
```

Phạm vi gồm Python, TypeScript, Bash, Terraform, Dockerfile, YAML/JSON/HTML
trong các thư mục application, deployment, infrastructure, observability và
scripts. Trivy không chạy trong lần này theo chỉ đạo operator; evidence này
không thay thế filesystem/image/secret scan Trivy hoặc SBOM/Cosign của release.
