# OBS-012 — Grafana Operations dashboard v2 (2026-08-12)

ConfigMap `kuberag-operations-dashboard` đã được áp dụng qua IAP. Đây là thay
đổi duy nhất: thêm hai panel Prometheus cho node workload CPU/RAM; không restart
application, không tạo PVC/VM và không thay firewall.

Grafana API nội bộ được xác nhận bằng credential Secret chỉ trong shell (không
in credential):

```text
Grafana dashboard kuberag-operations version=2 loaded
```

Hai panel dùng cAdvisor workload usage / machine capacity. Chúng không thay thế
host-OS metric của node exporter; công thức và số liệu snapshot ở
`OBS-003/gcp-node-workload-utilization-2026-08-12.md`.
