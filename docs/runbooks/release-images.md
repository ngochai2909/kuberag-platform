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

## Node identity của k3s trên GCP

Một **Kubernetes Node object** là danh tính mà kubelet đăng ký trong API
server; nó không hoàn toàn giống với VM. GCP có thể cung cấp hostname đầy đủ
như `kuberag-server.asia-southeast1-b.c.PROJECT.internal`. Nếu k3s dùng hostname
đó sau một lần restart trong khi trước đây dùng `kuberag-server`, cluster sẽ
thấy hai Node object cho cùng một VM: Node cũ `NotReady` và Node mới `Ready`.

Playbook đặt `node-name: kuberag-server` để danh tính này ổn định qua reboot và
reconfigure. Sau bất kỳ lần chạy playbook nào, kiểm tra đúng một Node `Ready`:

```bash
KUBECONFIG="$HOME/.kube/kuberag-gcp.yaml" kubectl get nodes -o wide
KUBECONFIG="$HOME/.kube/kuberag-gcp.yaml" kubectl get pods -A -o wide
```

Nếu còn một Node tên khác, **không xóa ngay**. Trước hết xác nhận
`kuberag-server` đã `Ready` và workload stateful (PostgreSQL, Prometheus, Loki,
Tempo) vẫn chạy trên nó. Chỉ sau đó mới xóa Node thừa bằng một checkpoint vận
hành riêng; thao tác này sẽ làm DaemonSet trên Node thừa bị dừng nhưng không xóa
PVC hay dữ liệu PostgreSQL.

## Release hiện tại: operator digests (2026-08-05)

CI release `cb6c0f0` remains the last fully scanned/Cosign-signed set in
evidence. The live three-node demo currently pins **operator-built** digests in
`deploy/kustomize/overlays/gcp-release/` after Tin/Chat + catalog work:

| Workload | Immutable image |
| --- | --- |
| RAG API (gồm init container) | `asia-southeast1-docker.pkg.dev/kube-rag-platform/kuberag/kuberag-api@sha256:dbbd725ebfd7b6acf02cf8779f46594f3b892813443a8dc49ff0817eaaeaec94` |
| Frontend | `asia-southeast1-docker.pkg.dev/kube-rag-platform/kuberag/kuberag-web@sha256:7e10d7c294168bd7a2286c38b1d96ff34a84448e48a79b153f354a8ed7fd6a06` |

Prefect/ingestion remains on the multi-feed operator digest previously rolled
out (`…16ba3c00…`). Re-pin through CI when the next `main` release job succeeds.

### Historical signed release: `cb6c0f0`

Workflow thành công của commit `cb6c0f07c9e0280f5fd2ac4a5ccaf356d59f0598`
đã quét, tạo SBOM và ký ba digest dưới đây (evidence `SEC-*`).

| Workload | Immutable image |
| --- | --- |
| RAG API (gồm init container) | `asia-southeast1-docker.pkg.dev/kube-rag-platform/kuberag/kuberag-api@sha256:3effa480d690775d75f7eaa251f585918378018253d15ceabafb64559cb3aa29` |
| Prefect server, worker và Job | `asia-southeast1-docker.pkg.dev/kube-rag-platform/kuberag/kuberag-ingestion@sha256:a6217acf0598a01400fd44b1f4fe030931145ad5a04b5362e26d27bd53373037` |
| Frontend | `asia-southeast1-docker.pkg.dev/kube-rag-platform/kuberag/kuberag-web@sha256:05181867af46b95469ffefc6b0e4543a1e68650b8d897967128dfeea4e5dbd25` |

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
