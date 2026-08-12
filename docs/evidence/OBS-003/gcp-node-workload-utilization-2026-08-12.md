# OBS-003 — node workload utilization (2026-08-12)

Prometheus được truy vấn qua port-forward loopback tạm thời trên VM. Không có
thay đổi cluster. `node_exporter` hiện tắt; hai query dưới đây dùng cAdvisor của
kubelet, vì vậy biểu thị tổng workload Kubernetes trên mỗi node, không gồm
process host operating system.

```promql
sum by (node) (rate(container_cpu_usage_seconds_total{container!="",image!=""}[5m]))
  / on (node) machine_cpu_cores

sum by (node) (container_memory_working_set_bytes{container!="",image!=""})
  / on (node) machine_memory_bytes
```

Kết quả tại thời điểm truy vấn:

| Node | CPU workload / capacity | RAM workload / capacity |
| --- | ---: | ---: |
| `kuberag-server` | 0.53% | 3.74% |
| `kuberag-worker-application` | 2.07% | 21.99% |
| `kuberag-worker-observability` | 4.74% | 17.32% |

Prometheus cũng trả ba series `machine_cpu_cores`: server 8 vCPU, application
worker 4 vCPU và observability worker 2 vCPU. Dashboard Git-provisioned
`KubeRAG Operations` version 2 chứa hai panel tương ứng. Để quan sát toàn bộ
host (kernel, process không thuộc container, disk I/O), phải bật node exporter
trong một rollout Helm riêng.
