# KubeRAG Operations Cheat Sheet

Tài liệu này là các lệnh vận hành hằng ngày cho cluster GCP single-node. Trừ
khi ghi rõ, các lệnh bên dưới là chỉ-đọc: không tạo VM, không đổi firewall và
không đổi dữ liệu.

## Bắt đầu

Kubeconfig GCP đã được nạp mặc định khi mở Bash mới. Terminal A giữ tunnel:

```bash
make gcp-k3s-tunnel
```

Terminal B dùng trực tiếp:

```bash
kubectl get nodes -o wide
kubectl get namespaces
kubectl -n rag get pods
```

Nếu tunnel dừng, `kubectl` và K9s sẽ không kết nối được API. Chạy lại tunnel,
không cần tạo lại cluster.

## Cluster và workload

```bash
kubectl get pods -A -o wide
kubectl get deployment,statefulset,daemonset,job,cronjob,pod,svc,pvc -A
kubectl -n rag get deploy,pods,svc,pvc -o wide
make gcp-llama-status
make gcp-rag-api-status
make gcp-prefect-status
```

- `1/1 Running`: container đã qua readiness probe.
- `PVC Bound`: storage bền vững đã gắn được vào Pod.
- `ClusterIP`: Service chỉ dùng trong cluster, không public Internet.

## K9s

```bash
# Chỉ namespace RAG.
k9s --readonly -n rag

# Toàn cluster.
k9s --readonly
```

```text
:pod       xem Pod
:deploy    xem Deployment
:svc       xem Service
:pvc       xem PersistentVolumeClaim
:events    xem Kubernetes events
l          xem log resource đang chọn
d          xem describe/chi tiết resource đang chọn
0          chuyển sang tất cả namespace
?          mở trợ giúp
:q         thoát
```

`--readonly` chặn thao tác sửa, xóa, scale hoặc restart. K9s cho trạng thái
realtime; Grafana lưu lịch sử metrics, logs, traces và profiles sau khi stack
observability được cài. Xem thêm [`observability.md`](observability.md).

## Logs, events và Pod lỗi

```bash
# Theo dõi log liên tục, thoát bằng Ctrl+C.
kubectl -n rag logs deployment/kuberag-llm --tail=100 -f
kubectl -n rag logs deployment/kuberag-rag-api --tail=100 -f

# Events mới nhất thường giải thích Pending, ImagePullBackOff hoặc probe lỗi.
kubectl -n rag get events --sort-by=.lastTimestamp

# Thay POD_NAME bằng tên từ kubectl get pods -n rag.
kubectl -n rag describe pod POD_NAME
kubectl -n rag logs POD_NAME --previous
```

`describe` có phần `Events`, cho biết scheduler, PVC, image, memory limit hoặc
health probe đã làm Pod không chạy. `--previous` đọc log trước lần restart gần
nhất.

## CPU, RAM, disk và VM

```bash
# Kubernetes metrics, nếu metrics-server đang sẵn sàng.
kubectl top nodes
kubectl top pods -A
kubectl top pods -n rag

# Trực tiếp trên VM.
ssh kuberag-gcp
free -h
df -h
lsblk
systemctl status k3s --no-pager
sudo k3s ctr images ls
sudo crictl ps -a
```

- `free -h`: RAM toàn VM. llama.cpp và E5 giữ model trong RAM sau query đầu.
- `df -h`: dung lượng filesystem; PVC nằm trên disk 150 GiB tại
  `/var/lib/kuberag`.
- `kubectl top`: mức dùng thực tế; khác `requests` và `limits` trong manifest.

## Kiểm tra llama.cpp

Terminal A:

```bash
kubectl -n rag port-forward service/kuberag-llm 18080:8080
```

Terminal B:

```bash
curl --silent http://127.0.0.1:18080/health
curl --silent http://127.0.0.1:18080/v1/models | jq
```

`/health` cần trả `{"status":"ok"}`. `/v1/models` cần có
`kuberag-qwen2.5-1.5b`. Dừng port-forward bằng `Ctrl+C`; tunnel này chỉ mở ở
localhost, không đổi firewall hay public model.

## Kiểm tra RAG end-to-end

Terminal A:

```bash
kubectl -n rag port-forward service/kuberag-rag-api 18000:80
```

Terminal B. GCP demo hiện không yêu cầu bearer token, nhưng vẫn chịu rate limit
chung ở Envoy. Lệnh này gọi model thật, vì vậy chỉ dùng khi cần xác minh:

```bash
curl --fail --silent --show-error http://127.0.0.1:18000/api/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Cac nguon tin nay den tu dau?","top_k":2}' | jq
```

Response có `answer`, `sources`, `request_id`, `trace_id`, `retrieval_ms`,
`generation_ms` và `total_ms`.

```text
FastAPI -> E5 embedding -> PostgreSQL/pgvector -> bounded prompt
        -> llama.cpp/Qwen -> answer + VnExpress source URLs
```

## Envoy routes, demo API, and rate limit

The API remains internal until the dedicated routing overlay is applied. Render
it first; rendering is local and does not change the cluster:

```bash
make gcp-rag-routing-render
```

After the operator has reviewed the render and applied it, Envoy routes
`http://VM_EXTERNAL_IP:8080/api/` to the internal `kuberag-rag-api` Service.
The GCP overlay explicitly enables `PUBLIC_DEMO_MODE`, allowing the same-origin
browser frontend to call this temporary demo API without exposing a bearer
token. The `BackendTrafficPolicy` allows 10 requests per minute for the whole
`/api/` route on the current single Envoy data-plane Pod; the next request is
rejected with HTTP `429` before FastAPI, PostgreSQL, or llama.cpp runs.

```bash
make gcp-rag-routing-status
make gcp-rag-routing-smoke
make gcp-rag-rate-limit-smoke
```

`gcp-rag-routing-smoke` makes one unauthenticated real RAG request, so it
consumes CPU time on the model Pod. Public demo mode is intentionally limited
to this single-node demonstration and must be replaced with real user or
gateway authentication before any broader deployment.

`gcp-rag-rate-limit-smoke` sends 11 valid JSON requests. The first ten may
reach the model unless the route has already consumed its shared quota; at
least one later request must be `429` from Envoy. It can consume model CPU and
the shared quota, so wait one minute before another API smoke test. This is a
lightweight configuration check, not the required k6 load-test evidence.

## Browser demo

The GCP frontend is a separate `kuberag-web` Deployment. Envoy serves the SPA
at the root path and FastAPI remains behind the same origin:

```text
Browser -> Envoy :8080 -> /           -> kuberag-web  -> Tin (category browse)
                       -> /chat       -> kuberag-web  -> Chat (RAG Q&A)
                       -> /api/v1/*   -> kuberag-rag-api -> catalog + query
                       -> /hostname   -> smoke Pod
```

SPA routes (client-side History API; Nginx falls back to `index.html` for
non-asset paths; `/assets/*` missing files return `404`):

- `/` — Tin: filter by `metadata.category`, cards open the VnExpress URL
- `/chat` — Chat: `POST /api/v1/query` with sources and timings

Catalog API (metadata only; never returns `documents.content`):

```bash
curl -sS "http://VM_EXTERNAL_IP:8080/api/v1/categories"
curl -sS "http://VM_EXTERNAL_IP:8080/api/v1/documents?category=tin-moi-nhat&limit=24"
```

Use the VM external IP that Terraform prints, for example:

```bash
make gcp-frontend-status
```

Then open `http://VM_EXTERNAL_IP:8080/` from a browser whose public egress IP
is in the Terraform firewall's administrator CIDRs. The page contains no
database credential, model credential, or bearer token. It is a temporary
unauthenticated demo endpoint; do not publish it beyond the restricted demo
network. Source cards show an RSS thumbnail only when the source document has
`metadata.image_url`.

## Lệnh thay đổi trạng thái

Không chạy các lệnh sau chỉ để kiểm tra. Chúng thay đổi cluster hoặc dữ liệu:

```bash
make gcp-rag-api-apply
make gcp-rag-routing-apply
make gcp-llama-apply
make gcp-observability-install
make gcp-observability-apply
make gcp-prefect-worker-restart
make gcp-ingest-run          # crawl/upsert PostgreSQL
kubectl delete ...
kubectl rollout restart ...
```

`terraform apply`, thay đổi firewall, stop/start VM và `terraform destroy` có
tác động cloud/cost lớn hơn. Xem `gcp-cost-control.md` trước khi chạy.

## Cluster local khi cần

GCP là mặc định. Dùng local cho đúng một lệnh mà không đổi toàn shell:

```bash
KUBECONFIG="$HOME/.kube/kuberag-k3s.yaml" kubectl get nodes
KUBECONFIG="$HOME/.kube/kuberag-k3s.yaml" k9s --readonly -n rag
```
