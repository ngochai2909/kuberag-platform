# PostgreSQL/pgvector single-node

Runbook này triển khai data layer tạm thời trên single-node k3s. Nó không tạo
tài nguyên GCP và không thay thế topology cuối gồm PostgreSQL primary/replica
trên các worker khác nhau.

## Kiến trúc và trách nhiệm

Luồng triển khai:

```text
Helm -> CloudNativePG operator + CRD
Kustomize -> Cluster kuberag-pg + Database kuberag
CloudNativePG -> PostgreSQL Pod + PVC + Services + generated Secrets
```

- **CloudNativePG (CNPG) operator** theo dõi custom resources (CR) trong
  namespace `data` và biến desired state thành PostgreSQL chạy thật. Chart
  `cnpg/cloudnative-pg` được pin ở `0.29.0`, tương ứng operator `1.30.0`.
- **Helm** cài phần mềm bên thứ ba là operator và các Custom Resource
  Definition (CRD). CRD mở rộng Kubernetes với các kind như `Cluster` và
  `Database`.
- **Kustomize** render manifest do dự án sở hữu. Base chung nằm tại
  `deploy/kustomize/base/postgresql`; overlay `local` và `gcp` là điểm để bổ
  sung khác biệt môi trường sau này.
- **Cluster CR** tạo một PostgreSQL 18 instance, một PersistentVolumeClaim
  (PVC) 20 GiB trên StorageClass `local-path`, user/database ứng dụng
  `kuberag`, resource requests/limits và generated application Secret.
- **Database CR** quản lý database `kuberag` và extension SQL `vector`.
  PostgreSQL là database server; `pgvector` là extension thêm kiểu `vector`
  cùng toán tử/index similarity search. Image `standard` đã chứa file pgvector,
  còn Database CR thực hiện bước bật extension trong database.

Luồng dữ liệu ở phase sau:

```text
Source -> Prefect -> embedding -> kuberag-pg-rw -> PostgreSQL/pgvector
FastAPI -> kuberag-pg-rw -> vector similarity search
```

Ứng dụng phải dùng Service ổn định `kuberag-pg-rw`, không dùng Pod IP.
`*-rw` luôn trỏ tới instance có quyền read-write; Pod IP có thể đổi khi CNPG
reconcile hoặc restart Pod.

### Database bootstrap và Database CR

`bootstrap.initdb` tạo database và owner `kuberag` đúng một lần khi data
directory còn rỗng. Database CR có thể quản lý chính database đã được bootstrap:
CNPG dùng `ALTER DATABASE` cho database đã tồn tại và reconcile extension bằng
`CREATE/ALTER EXTENSION`. Vì vậy hai resource không tạo database trùng nhau.

`databaseReclaimPolicy: retain` được khai báo rõ để việc xóa nhầm Database CR
không yêu cầu CNPG xóa database PostgreSQL tương ứng. Đây không phải cơ chế
backup và không bảo vệ trước việc xóa `Cluster`, PVC hoặc disk.

## Storage single-node

Trên GCP, Ansible mount Persistent Disk 150 GiB tại `/var/lib/kuberag` và đặt
k3s data directory tại `/var/lib/kuberag/k3s`. Local Path Provisioner lưu dữ
liệu PVC bên dưới:

```text
/var/lib/kuberag/k3s/storage
```

PVC 20 GiB là yêu cầu dung lượng logic bên trong disk 150 GiB; nó không tạo
thêm GCP disk. `local-path` gắn dữ liệu với duy nhất node hiện tại, nên không
cung cấp high availability hoặc node failover. Disk 150 GiB vẫn phát sinh chi
phí khi VM dừng và sẽ mất nếu disk bị destroy theo Terraform.

## Checkpoint 0: preflight chỉ đọc/local

Các lệnh này không thay đổi Kubernetes hoặc GCP. Chart được đọc trực tiếp từ
OCI registry của CloudNativePG nên không phụ thuộc cấu hình Helm repo cục bộ.

```bash
kubectl version --client
helm version
helm show chart \
  oci://ghcr.io/cloudnative-pg/charts/cloudnative-pg \
  --version 0.29.0
```

Kết quả mong đợi: client tools hoạt động; chart hiển thị `version: 0.29.0` và
`appVersion: 1.30.0`. Nếu chart không tìm thấy, kiểm tra DNS/proxy và chạy lại
`helm repo update cnpg`. Không chuyển sang chart version khác để né lỗi.

Trước khi thao tác GCP cluster, giữ SSH/IAP tunnel ở một terminal:

```bash
make gcp-k3s-tunnel
```

Ở terminal khác, `make gcp-k3s-status` phải cho thấy node `Ready`. Đây vẫn là
kiểm tra chỉ đọc.

## Checkpoint 1: render local, không apply

Hai target sau chỉ render YAML ra stdout. Chúng không liên hệ Kubernetes API và
không tạo Pod, PVC, Secret hay chi phí cloud:

```bash
make cnpg-render
make postgresql-render
```

`cnpg-render` kiểm tra pinned chart với
`deploy/helm/cloudnative-pg/values.yaml`. `postgresql-render` kiểm tra base và
cả hai overlay. Thành công nghĩa là cú pháp/template render được; chưa chứng
minh CR được operator reconcile hay PostgreSQL chạy được.

## Checkpoint 2: cài operator — thay đổi cluster

Điểm dừng: chỉ chạy sau khi đã review output render và phê duyệt riêng cho việc
thay đổi GCP Kubernetes cluster. Lệnh không tạo VM/disk mới nhưng tạo
Deployment, RBAC và CRD trong cluster:

```bash
make gcp-cnpg-install
```

Operator được cài vào namespace `data`, với `config.clusterWide: false`, nên
chỉ theo dõi namespace đó. Kết quả mong đợi là
`deployment/cloudnative-pg` đạt `Available`. Nếu timeout, xem:

```bash
KUBECONFIG="$HOME/.kube/kuberag-gcp.yaml" \
  kubectl --namespace data get pods
KUBECONFIG="$HOME/.kube/kuberag-gcp.yaml" \
  kubectl --namespace data describe deployment/cloudnative-pg
```

Các lệnh chẩn đoán trên chỉ đọc. Không nới RBAC hoặc Pod Security cho toàn
cluster để xử lý lỗi chart.

## Checkpoint 3: tạo PostgreSQL — thay đổi cluster và storage

Điểm dừng: chỉ chạy sau khi operator `Available` và có phê duyệt riêng cho việc
tạo PostgreSQL/PVC:

```bash
make gcp-postgresql-apply
```

Lệnh apply GCP overlay, tạo `Cluster/kuberag-pg` và `Database/kuberag`. CNPG sẽ
pull image đã pin bằng digest, tạo PVC 20 GiB, Pod, Services và Secrets. Việc
ghi dữ liệu vào disk có tác động persistence; không có external network
exposure vì Services là ClusterIP.

## Xác minh trạng thái chỉ đọc

```bash
make gcp-postgresql-status
```

Kết quả cần kiểm tra:

- Deployment operator tồn tại.
- `Cluster/kuberag-pg` có một instance ready.
- `Database/kuberag` có trạng thái applied.
- PostgreSQL Pod ở `Running`/ready và PVC ở `Bound`.
- Service `kuberag-pg-rw` tồn tại.
- Secret `kuberag-pg-app` tồn tại; lệnh status chỉ hiện metadata, không giải mã.

Để xác minh extension sau khi cluster healthy, dùng CNPG plugin hoặc một Pod
client tạm thời ở checkpoint kiểm thử được phê duyệt, rồi chạy SQL:

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';
```

Cần thấy đúng một dòng `vector`. Manifest và trạng thái resource không thay thế
bằng chứng SQL cho DB-004.

## Alembic migration và vector integration

Migration được sở hữu bởi ingestion data layer tại
`apps/ingestion/migrations`. Revision đầu tạo `documents`, `chunks`,
`ingestion_runs`, các foreign key/unique/check constraints và cột
`chunks.embedding` kiểu `vector` chưa cố định dimension. HNSW/IVFFlat chưa
được tạo cho tới khi embedding model, dimension và distance metric được pin.

Render SQL offline trước khi kết nối database:

```bash
make migration-sql
```

Để chạy migration trên GCP, máy local phải SSH được qua alias `kuberag-gcp`.
Target dưới đây mở một tunnel tạm tới Service `kuberag-pg-rw`, đọc URI từ
Secret vào biến môi trường của đúng process và đóng tunnel khi lệnh kết thúc:

```bash
make gcp-db-migrate
make gcp-db-current
```

Script không ghi URI/password ra file hoặc stdout. Không thêm `set -x`, không
echo `DATABASE_URL`, và không lưu URI lấy từ Secret vào `.env`.

`alembic upgrade head` lần đầu phải tạo schema từ database rỗng. Chạy lần hai
phải thành công như no-op để chứng minh DB-006:

```bash
make gcp-db-migrate
make gcp-db-migrate
```

Sau migration, chạy integration test synthetic trong transaction rồi rollback:

```bash
make gcp-db-vector-test
```

Test thêm một document và hai vector 3 chiều, truy vấn cosine distance, xác nhận
chunk gần nhất rồi rollback. Vector 3 chiều chỉ là fixture DB-007; schema vẫn
dùng `vector` không cố định dimension và chưa quyết định embedding model.

## Generated Secret

CNPG tạo Secret ứng dụng `kuberag-pg-app`, chứa username/password và connection
information. Secret phụ thuộc vào `Cluster`; ứng dụng phase sau tham chiếu bằng
`secretKeyRef`, không copy giá trị sang manifest, `.env`, log hoặc tài liệu.

Không chạy các lệnh như `kubectl get secret ... -o yaml`, base64 decode, chụp
màn hình hoặc paste giá trị Secret vào chat/evidence. `kubectl get
secret/kuberag-pg-app` không có output data value và phù hợp để xác nhận Secret
tồn tại. Kubeconfig cũng là dữ liệu nhạy cảm và không được commit.

## Lỗi thường gặp

- **`no matches for kind "Cluster"` hoặc `"Database"`**: CRD chưa được cài hoặc
  operator/chart sai version. Cài operator trước rồi xác nhận CRD của CNPG 1.30;
  không bỏ Database CR khỏi manifest để né lỗi.
- **Operator không thấy Cluster**: chart bị cài khác namespace trong khi
  `clusterWide: false`. Operator và CR phải cùng namespace `data`.
- **Pod `Pending`**: kiểm tra PVC, StorageClass `local-path`, free disk và
  resource availability. Không xóa PVC để “thử lại”.
- **`ImagePullBackOff`**: kiểm tra Internet/GHCR và digest. Không đổi sang
  `latest` hoặc bỏ digest.
- **Database CR không applied**: kiểm tra Cluster đã ready, owner `kuberag` tồn
  tại và operator logs đã redaction. Database bootstrap hoàn tất trước khi
  extension được reconcile.
- **`extension "vector" is not available`**: xác nhận đang chạy đúng image
  `standard` đã pin; variant `minimal` không có cùng bundle extension. Không
  tự cài package vào container đang chạy.
- **Disk đầy**: kiểm tra `/var/lib/kuberag` và PVC usage. Disk đầy có thể làm
  PostgreSQL dừng để bảo vệ consistency. Không xóa file trong PGDATA thủ công.
- **Single node hoặc disk lỗi**: database unavailable; một instance không có
  replica để promote. Persistence test chỉ chứng minh Pod restart, không chứng
  minh node failover.

## Cảnh báo an toàn, chi phí và giới hạn

- Không xóa `Cluster/kuberag-pg`, PVC, PersistentVolume, namespace `data`, CNPG
  CRD hoặc GCP disk. Không thêm target delete/uninstall cho data layer.
- Xóa Pod có chủ đích là persistence test `DB-010` (đã Pass trên GCP), không
  phải cách sửa lỗi mặc định; phải ghi checksum/count trước và sau.
- Replica không phải backup. Mốc single-node hiện chưa có cả replica lẫn
  backup/restore; mất disk có thể mất toàn bộ dữ liệu.
- PostgreSQL và operator không được public qua firewall/Gateway. Chỉ workload
  trong cluster dùng ClusterIP Service và Secret.
- Resource limits giảm nguy cơ chiếm toàn node nhưng có thể gây throttling/OOM;
  phải quan sát trước khi tăng. Tăng VM/disk có thể tăng chi phí GCP.
- Budget alert chỉ cảnh báo, không tự giới hạn chi tiêu.

Evidence runtime cho DB-001/DB-003/DB-004/DB-010 chỉ được ghi sau khi các lệnh
thực sự chạy trên cluster và output đã được redaction. Render local không đủ để
đánh dấu acceptance criterion là `Pass`.
