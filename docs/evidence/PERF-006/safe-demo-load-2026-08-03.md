# PERF-006 — safe demo load conclusion

Mức tải demo an toàn đã được kiểm chứng trên single-node hiện tại là ramp tối
đa **3 VU**, mỗi VU có think time 35 giây, đi qua Envoy và thực hiện RAG thật.

- 9/9 query thành công; p95 end-to-end 2,458 giây; response nào cũng có answer,
  source, request ID và trace ID.
- Node sau tải và sau rate-limit alert chỉ dùng 30% RAM; không có Pod restart
  hoặc PVC lỗi.
- Nút nghẽn công suất cực đại **chưa được xác định**: scenario bị giới hạn có
  chủ đích bởi shared Envoy 10 request/phút và tài nguyên CPU-only llama.cpp.

Vì vậy, 3 VU là **safe bound đã chứng minh**, không phải cam kết throughput
production hay maximum capacity. Muốn tăng tải phải có checkpoint xác nhận mới,
theo dõi RAM 85%/workload 90% limit và tránh thay đổi rate-limit production.

