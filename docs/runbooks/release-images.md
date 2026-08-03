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

## Release hiện tại: `24a106b`

Workflow thành công của commit `24a106b06c73de55f6dcfc472367e655b2d4917f`
đã quét, tạo SBOM và ký ba digest dưới đây. Release overlay tại
`deploy/kustomize/overlays/gcp-release/` là bản ghi Git của đúng release này.

| Workload | Immutable image |
| --- | --- |
| RAG API (gồm init container) | `asia-southeast1-docker.pkg.dev/kube-rag-platform/kuberag/kuberag-api@sha256:41d5e6b962d4d2d320a8723898a2c05f995734131422be40ee63e5c3d7589dd5` |
| Prefect server, worker và Job | `asia-southeast1-docker.pkg.dev/kube-rag-platform/kuberag/kuberag-ingestion@sha256:046e3751b3d56b173a6d04eeb4d0e67a494b9c7340d1c35ba74ef274b59a0984` |
| Frontend | `asia-southeast1-docker.pkg.dev/kube-rag-platform/kuberag/kuberag-web@sha256:ff429d39e6ec6d97e3cd0ef28e72c0047098f57d1bbd7e6dced324b54f932f7c` |

Các base manifest vẫn dùng `*:local` và `imagePullPolicy: Never` cho phát
triển local. Release overlay thay cả image bằng digest và policy bằng
`IfNotPresent`: kubelet sẽ pull image đúng digest lần đầu từ Artifact Registry
bằng node service account có quyền reader, sau đó có thể dùng cache. Vì digest
không thay đổi nội dung, cache không làm Pod chạy image khác release.

### Checkpoint rollout

```bash
# Chỉ render tại máy local; không đổi Kubernetes.
make gcp-release-render

# Thay đổi cluster: rollout bốn Deployment dài hạn, không tự chạy Prefect Job.
make gcp-release-apply

# Chỉ đọc: Ready state và image thực tế trong Pod template.
make gcp-release-status
```

Chỉ chạy `gcp-release-apply` sau khi release-manifest PR đã được review và có
xác nhận ngay trước rollout. Nếu rollout lỗi, đổi ba digest trong một PR mới về
release đã biết là tốt rồi apply lại; không đổi tag hay import image local để
rollback.

Các Job có side effect được tách khỏi rollout: dùng
`make gcp-release-prefect-bootstrap`, `make gcp-release-e5-download`,
`make gcp-release-e5-smoke` hoặc `make gcp-release-ingest-run` khi chủ động
muốn chạy đúng Job đó. `gcp-release-ingest-run` có thể fetch/upsert dữ liệu nên
cần checkpoint xác nhận riêng.

## Private pull trên k3s Compute Engine

Khác GKE, k3s tự quản lý không tự chuyển service account của VM thành registry
credential. Playbook GCP cài kubelet credential provider tại node; provider chỉ
match `asia-southeast1-docker.pkg.dev`, lấy access token ngắn hạn từ GCE metadata
service và trả token trực tiếp cho kubelet. Token không được lưu vào Git, Secret
Kubernetes hoặc disk. Provider phụ thuộc VM service account
`kuberag-node` có `roles/artifactregistry.reader` và scope `cloud-platform`.

Thay đổi provider restart k3s nên phải render/review Ansible, xác nhận riêng
trước apply, rồi xác minh node `Ready` trước release rollout. Không dùng
service-account key, `imagePullSecret` token dài hạn hay public Artifact Registry.
