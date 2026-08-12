# KubeRAG Architecture — STD-DIAG source

Thư mục này là **nguồn thiết kế có thể review bằng Git** cho KubeRAG. Mỗi sơ đồ
dùng Mermaid trong Markdown; PDF hoặc ảnh chỉ là bản export khi cần trình bày.
Nó áp dụng chuẩn STD-DIAG tham chiếu tại [`../architecture.pdf`](../architecture.pdf).

## Cách đọc

| Tài liệu | Cấp / grain | Câu hỏi trả lời |
| --- | --- | --- |
| [L1 context](l1-context.md) | L1 / toàn hệ thống | KubeRAG phục vụ ai và chạm hệ nào bên ngoài? |
| [L2 integration](l2-integration.md) | L2 / bounded context (BC) | Các trách nhiệm cấp hệ tích hợp ra sao? |
| [L2 data ownership](l2-data-ownership.md) | L2 / aggregate logic | Ai sở hữu dữ liệu nào và ranh giới nhất quán ở đâu? |
| [L2 RAG sequence](l2-rag-query-sequence.md) | L2 / BC | Một truy vấn RAG đi qua các BC nào? |
| [L2 deployment](l2-deployment-gcp.md) | L2 / hạ tầng | Workload chạy ở đâu, đường vào/ra nào? |
| [L2 security and quality](l2-security-quality.md) | L2 / trust zone, NFR | Ranh giới tin cậy và đánh đổi chất lượng là gì? |
| [L3 RAG API](l3-rag-api.md) | L3 / module và process | Bên trong RAG API tổ chức và xử lý lỗi thế nào? |
| [L3 ingestion](l3-ingestion.md) | L3 / module, process, schema | Ingestion xử lý từng bài và upsert thế nào? |

`docs/data-model.md` vẫn là mô tả contract nguồn và schema chi tiết; tài liệu
L2/L3 ở đây liên kết tới nó, không tạo một schema thứ hai cạnh tranh.

## Quy ước bắt buộc

- Mỗi sơ đồ chỉ dùng **một grain** ghi trong phần đầu tài liệu.
- Ý nghĩa mũi tên được khai báo theo loại view; không suy diễn ý nghĩa từ màu.
- Trong L2 integration: nét liền là gọi đồng bộ, nét đứt là event/telemetry
  bất đồng bộ. Trong L3 module: mũi tên là phụ thuộc lúc biên dịch. Trong
  deployment/C&C: mũi tên là chiều khởi tạo kết nối.
- Màu phân vai nhất quán: xanh dương = BC/workload do KubeRAG sở hữu, xanh lá
  = hệ ngoài, tím = datastore, đỏ = luồng/tài sản nhạy cảm, xám = hạ tầng.
- Một view giữ khoảng `7 ± 2` node; chi tiết được tách sang view hoặc bảng.

## Nguồn sự thật và trạng thái

Các quyết định phạm vi lấy từ [`../PROJECT_SCOPE.md`](../PROJECT_SCOPE.md),
stack từ [`../TECH_STACK.md`](../TECH_STACK.md), kiến trúc nền từ
[`../ARCHITECTURE.md`](../ARCHITECTURE.md), còn trạng thái runtime chỉ được
khẳng định khi có evidence hoặc kiểm tra thật.

Khi rà soát ngày 2026-08-11 có các chênh lệch cần xử lý, không được che trong
sơ đồ:

- Overlay ba node pin `prefect-server` vào worker `application`
([manifest](../../deploy/kustomize/overlays/gcp-three-node/prefect/kustomization.yaml)),
nhưng Pod runtime lúc kiểm tra vẫn ở `kuberag-server`. L2 deployment ghi cả
trạng thái mong muốn và trạng thái quan sát này; cần rollout/kiểm tra riêng
trước khi coi placement đã đồng bộ.
- [`../data-model.md`](../data-model.md) vẫn dùng ngôn ngữ “planned/production
  will use” cho E5, trong khi composition root và runtime đã dùng
  `E5EmbeddingProvider`. Đây là tài liệu cần đồng bộ trạng thái, không phải lý
  do để thêm một embedding provider thứ hai.
- Ví dụ `top_k: 5` trong [`../ARCHITECTURE.md`](../ARCHITECTURE.md) không phải
  default implementation: model API và frontend hiện mặc định/gửi `3`. Chỉ đổi
  default sau khi chủ dự án xác nhận thay đổi public behavior và benchmark lại.

## Quy trình cập nhật

1. Thay đổi trách nhiệm, integration, data ownership hoặc trust boundary:
   cập nhật L2 tương ứng trong cùng thay đổi.
2. Thay đổi module, schema, timeout, retry hay state machine của một BC: cập
   nhật L3 của BC đó.
3. Thay đổi hạ tầng: cập nhật deployment sau khi Terraform/Ansible/Kustomize
   đã được review; không dùng sơ đồ như lệnh áp dụng cloud.
4. Khi runtime khác manifest, ghi discrepancy và evidence trước; không tự sửa
   sơ đồ để che khác biệt.
