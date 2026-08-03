# Prefect metadata trên PostgreSQL

## Mục tiêu

Prefect Server lưu metadata điều phối trong PostgreSQL thay vì SQLite. Metadata
này gồm deployment, cron schedule, work pool, flow run và task run; nó không
phải dữ liệu bài báo, chunk hay embedding của KubeRAG.

```text
Prefect server/worker/UI -> database prefect, role prefect
Ingestion + RAG API     -> database kuberag, role kuberag
                         \-> cùng Cluster/kuberag-pg và Service kuberag-pg-rw
```

Tách database và role giúp giới hạn quyền theo workload. PostgreSQL hỗ trợ
nhiều request đọc/ghi đồng thời tốt hơn SQLite, nên tránh lỗi
`sqlite3 database is locked` khi scheduler, worker và UI cùng cập nhật state.

## Thành phần được quản lý

- `DatabaseRole/prefect` trong namespace `data` tạo login role không có
  `superuser`, `createdb` hoặc `createrole`.
- `Database/prefect` có owner `prefect` và reclaim policy `retain`.
- Secret `data/prefect-db-auth` là `kubernetes.io/basic-auth`, chỉ chứa
  username/password của role `prefect` và không được commit.
- Script sync tạo `prefect/prefect-server-db` chỉ có URI
  `postgresql+asyncpg://.../prefect`; Prefect Server đọc URI qua
  `secretKeyRef`.

Secret role ở namespace `data` vì CNPG `DatabaseRole` chỉ đọc Secret cùng
namespace. Secret runtime được copy có chủ đích sang namespace `prefect`, vì
Kubernetes không cho Pod mount Secret từ namespace khác.

## Tác động và rollback

Đây không phải migration dữ liệu Prefect từ SQLite sang PostgreSQL. Deployment,
schedule và lịch sử run trong SQLite cũ không được copy sang database mới.
PVC `prefect-server-data` cũ được giữ lại ngoài manifest để rollback cho đến
khi checkpoint được xác minh. Dữ liệu VnExpress, `documents`, `chunks`,
embeddings và `ingestion_runs` trong database `kuberag` không bị thay đổi.

Không xóa PVC SQLite cũ, database `prefect`, `DatabaseRole/prefect` hay Secret
khi đang xử lý sự cố. Rollback chỉ nên được thực hiện bằng manifest/revision
đã review, rồi rollout lại Prefect Server.

## Triển khai trên GCP

Giữ IAP Kubernetes tunnel ở một terminal:

```bash
make gcp-k3s-tunnel
```

Ở terminal khác, chạy từng checkpoint. Các lệnh dưới thay đổi Secret hoặc
cluster nhưng không tạo VM, disk hay firewall mới.

```bash
make gcp-prefect-role-secret
make gcp-postgresql-apply
make gcp-prefect-server-db-secret
make gcp-prefect-apply
make gcp-prefect-bootstrap
```

`gcp-prefect-role-secret` tạo password ngẫu nhiên khi Secret chưa tồn tại; nếu
Secret đã tồn tại, lệnh giữ nguyên password để idempotent. Không dùng `set -x`,
không decode Secret ra terminal và không lưu URI vào `.env`.

Sau database mới, Prefect cần bootstrap lại work pool/deployment. Rollout lại
worker một lần để xóa kết nối HTTP cũ giữ từ lúc server đổi database:

```bash
make gcp-prefect-worker-restart
```

## Lịch crawl hằng ngày

Lịch được khai báo trong Git tại
`apps/ingestion/src/ingestion/flows/ingest.py`. Cấu hình hiện tại là
`0 3 * * *` với timezone `UTC`, tương đương **10:00 giờ Việt Nam**. Giữ cron
ở UTC giúp timestamp và vận hành cloud nhất quán.

Sau khi đổi cron, cần build/import lại image ingestion rồi chạy Bootstrap Job
để cập nhật deployment đã có. Bootstrap chỉ đăng ký lịch; nó không crawl:

```bash
make gcp-ingestion-image-import
make gcp-prefect-bootstrap
```

Log Bootstrap phải có `schedule={'cron': '0 3 * * *', 'timezone': 'UTC'}`.
Evidence runtime hiện tại nằm tại
`docs/evidence/ING-005/gcp-prefect-schedule-1000-vietnam.txt`.

## Xác minh

Các lệnh sau chỉ đọc trạng thái hoặc logs, không in credential:

```bash
KUBECONFIG="$HOME/.kube/kuberag-gcp.yaml" \
  kubectl -n data get databaserole/prefect database/prefect

make gcp-prefect-status
```

Kết quả cần có:

- `DatabaseRole/prefect` và `Database/prefect` được CNPG reconcile thành công.
- `prefect-server` và `prefect-worker` có Pod `Running`/`Ready`.
- Prefect UI mở qua port-forward, deployment `kuberag-daily-ingest/daily` có
  schedule mới.
- Một manual run hoàn thành và log Prefect không còn `database is locked`.

Sau khi Prefect database ổn định, chạy `make gcp-ingest-run` để xác minh một
ingestion run thật. Lệnh này crawl VnExpress và có thể ghi dữ liệu mới vào
database KubeRAG.
