# Immutable image release path

## Mục tiêu

Artifact Registry là registry vùng `asia-southeast1` cho ba image custom:
`kuberag-api`, `kuberag-ingestion`, và `kuberag-web`. Terraform tạo repository
Docker có immutable tags, giữ hai version mới nhất, dọn artifact cũ/untagged
sau bảy ngày, và cấp VM đúng quyền `roles/artifactregistry.reader`. CI dùng
GitHub OpenID Connect (OIDC) federation để nhận tạm thời quyền writer; không
có service-account key.

Image digest là hash nội dung bất biến; tag Git SHA giúp con người tìm release,
nhưng Kubernetes release phải tham chiếu `image@sha256:...`, không chỉ tag.

## Checkpoint Terraform

`terraform plan` chỉ đọc GCP APIs và tính thay đổi. Nó sẽ cho thấy Artifact
Registry, hai service account, IAM binding, Workload Identity Pool/provider và
service account mới trên VM. Việc `apply` có thể dừng/start VM để gắn identity
và tạo chi phí lưu image; cần xác nhận riêng ngay trước apply.

```bash
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -out=tfplan
terraform -chdir=infra/terraform show tfplan
```

Sau apply, đặt hai GitHub repository variables (không phải secret) từ outputs:
`GCP_WIF_PROVIDER` và `GCP_ARTIFACT_WRITER_SA`; đặt `GCP_PROJECT_ID` là project
ID. Provider còn kiểm tra đúng repository `ngochai2909/kuberag-platform` và
`refs/heads/main`, nên pull request không thể push image.

Trong GitHub, mở **Settings → Secrets and variables → Actions → Variables**
và đặt chính xác:

| Variable | Giá trị |
| --- | --- |
| `GCP_PROJECT_ID` | `kube-rag-platform` |
| `GCP_WIF_PROVIDER` | `projects/121803788165/locations/global/workloadIdentityPools/kuberag-github/providers/github` |
| `GCP_ARTIFACT_WRITER_SA` | `kuberag-github-release@kube-rag-platform.iam.gserviceaccount.com` |

Đây là định danh công khai, không phải service-account key hay webhook. Không
đặt chúng vào GitHub Secrets vì workflow chỉ cần biến thường và OIDC sẽ cấp
credential ngắn hạn khi job `main` chạy.

## CI và deploy

CI kiểm tra Python API/ingestion và frontend, chạy Semgrep cùng Trivy filesystem
/config/secret scan. Chỉ push `main` mới build/push ba image, scan image mức
HIGH/CRITICAL, xuất CycloneDX SBOM, Cosign keyless sign/verify từng digest và
in digest vào job summary. Operator sao chép ba digest đó vào manifest release
được review trong Git trước deploy; không import local image hay dùng mutable
tag cho release.

Manifest nền hiện dùng `*:local` để phục vụ demo local-image tạm thời. Chỉ sau
khi job CI thành công, tạo PR release thay các reference đó bằng ba digest CI
in ra. Review PR phải xác nhận đầy đủ API (kể cả init container), Prefect
worker/server/jobs và frontend đều dùng `image@sha256:...` cùng release; sau đó
mới được apply cluster. Không tạo digest giả hoặc dùng Git SHA tag thay digest.

Base Python Chainguard trong hai Dockerfile đã pin digest ngày 2026-08-01;
frontend đã pin Node/Nginx. Pin giảm thay đổi bất ngờ nhưng cần review/refresh
định kỳ để nhận security fixes.
