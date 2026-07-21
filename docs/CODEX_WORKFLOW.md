# Quy trình dùng Codex cho KubeRAG

## 1. Vai trò của Codex

Codex là pair engineer hỗ trợ:

- Khám phá và giải thích repository.
- Lập kế hoạch migration/implementation.
- Viết hoặc refactor code, manifests, IaC và tests.
- Chạy lệnh kiểm tra trong môi trường được cấp quyền.
- Debug dựa trên output/log cụ thể.
- Review diff, security, regression và test gaps.
- Viết tài liệu và runbook khớp implementation.

Codex không tự quyết định chi phí cloud, secret, thay đổi scope hoặc destructive action. Người thực hiện phải review diff, phê duyệt thay đổi đáng kể và hiểu kết quả trước khi merge.

## 2. Thông tin Codex phải đọc trước khi code

Theo thứ tự:

1. `AGENTS.md`
2. `docs/PROJECT_SCOPE.md`
3. `docs/ARCHITECTURE.md`
4. `docs/TECH_STACK.md`
5. Milestone tương ứng trong `docs/ROADMAP.md`
6. Acceptance IDs tương ứng trong `docs/ACCEPTANCE_CRITERIA.md`
7. Code, tests và config liên quan trực tiếp

Nếu tài liệu mâu thuẫn với code, Codex phải báo cáo khác biệt và đề xuất hướng xử lý, không tự âm thầm chọn một bên.

## 3. Cấu trúc một prompt tốt

Mọi prompt triển khai nên có:

```text
Mục tiêu:
Bối cảnh:
Phạm vi được phép thay đổi:
Ràng buộc:
Tiêu chí hoàn thành:
Lệnh kiểm tra:
Không được làm:
Đầu ra báo cáo:
```

Một task nên đủ nhỏ để implement và verify trong 0.5–2 ngày. Không giao “làm toàn bộ dự án” trong một prompt.

## 4. Prompt khởi đầu: chỉ phân tích source-base

```text
Hãy đọc toàn bộ repository, bắt đầu từ AGENTS.md và các tài liệu trong docs/.

Bối cảnh:
Repository hiện tại là FastAPI source base cho OpenAI/LangGraph Agent. Mục tiêu mới là
KubeRAG: nền tảng RAG cloud-native sử dụng PostgreSQL/pgvector và llama.cpp self-hosted.

Mục tiêu của lượt này:
Đánh giá khoảng cách giữa repository hiện tại và kiến trúc KubeRAG.

Ràng buộc:
- Chưa sửa bất kỳ file nào.
- Không tự đề xuất thay stack đã chốt trong docs/TECH_STACK.md.
- Phân biệt required và optional.
- Ưu tiên giữ app factory, settings, error handling, request ID, structured logs,
  health checks, tests và CI nếu chúng còn phù hợp.
- Xác định rõ code LangGraph/OpenAI nào phải bỏ hoặc thay.

Đầu ra bắt buộc:
1. Tóm tắt repository hiện tại.
2. Danh sách giữ lại, sửa, xóa và bổ sung.
3. Cấu trúc monorepo đề xuất.
4. Kế hoạch migration theo các PR nhỏ, có dependency.
5. Acceptance IDs của từng PR.
6. Rủi ro và chiến lược test.
7. Đề xuất phase đầu tiên, nhưng chưa implement.
```

## 5. Prompt chuẩn bị monorepo

```text
Hãy triển khai duy nhất phase chuẩn bị monorepo đã được duyệt.

Mục tiêu:
- Chuyển backend hiện tại vào apps/rag-api mà không làm mất lịch sử logic.
- Tạo skeleton apps/ingestion, apps/frontend, infra, deploy, observability và tests/k6.
- Cập nhật tên dự án, README, Makefile và đường dẫn CI cần thiết.
- Chưa implement PostgreSQL, ingestion, LLM hoặc observability.

Ràng buộc:
- Giữ cho backend hiện tại vẫn chạy và test được sau khi di chuyển.
- Không thêm production dependency mới.
- Không thay đổi public API trong phase này.
- Không tạo secret hoặc credential mẫu có giá trị thật.

Hoàn thành khi:
- Cấu trúc thư mục khớp docs/ARCHITECTURE.md.
- Lint, typecheck và tests hiện có pass tại vị trí mới.
- README hướng dẫn lệnh mới.
- CI chạy đúng path.
- Diff đã được review và không chứa thay đổi ngoài scope.

Cuối cùng báo cáo file thay đổi, lệnh đã chạy, kết quả và phần còn lại.
```

## 6. Prompt refactor Agent thành RAG API skeleton

```text
Hãy triển khai RAG API skeleton trong apps/rag-api.

Mục tiêu:
- Loại bỏ dependency và code OpenAI/LangGraph Agent không thuộc required scope.
- Giữ app factory, settings, error handling, request ID, JSON logging,
  health endpoints và cách tổ chức tests còn phù hợp.
- Tạo interface Retriever và Generator độc lập provider.
- Tạo POST /api/v1/query sử dụng dependency giả trong tests.
- Response gồm answer, sources, request_id, trace_id, retrieval_ms,
  generation_ms và total_ms.

Ràng buộc:
- Chưa kết nối PostgreSQL hoặc llama.cpp thật trong PR này.
- Không dùng LangChain/LangGraph.
- Không thêm rate limit trong FastAPI.
- Unit tests không gọi network.
- Public errors không lộ stack trace hoặc secret.

Tiêu chí hoàn thành:
- RAG-001, RAG-006, RAG-008 và phần skeleton của RAG-009 được đáp ứng.
- Lint, format check, mypy và pytest pass.
- Coverage không thấp hơn baseline đã chốt.
- README và .env.example được cập nhật.
```

## 7. Prompt cho mỗi feature

```text
Hãy thực hiện issue [ISSUE-ID] tương ứng acceptance criteria [ACCEPTANCE-IDS].

Mục tiêu:
[Mô tả một hành vi cần thay đổi]

Bối cảnh:
[Files, service, sơ đồ hoặc lỗi liên quan]

Phạm vi được phép:
[Danh sách thư mục/file được sửa]

Ràng buộc:
- Tuân thủ AGENTS.md và tài liệu kiến trúc.
- Không thêm công nghệ/dependency ngoài scope nếu chưa được phê duyệt.
- Không sửa file ngoài phạm vi trừ khi thật sự cần; phải giải thích.
- Không commit secret.
- Không tuyên bố test pass nếu chưa chạy.

Hoàn thành khi:
- [Hành vi runtime cụ thể]
- [Tests cụ thể]
- [Telemetry/security/docs cụ thể]
- [Acceptance IDs có evidence]

Quy trình:
1. Đọc code và tests liên quan.
2. Nêu kế hoạch ngắn trước khi sửa.
3. Implement thay đổi nhỏ nhất đúng yêu cầu.
4. Viết/cập nhật tests.
5. Chạy narrow tests rồi full relevant checks.
6. Review diff cho bug, security và scope creep.

Kết thúc bằng báo cáo:
- Files đã thay đổi.
- Quyết định quan trọng.
- Lệnh kiểm tra và kết quả thật.
- Rủi ro/phần chưa xác minh.
- Commit message đề xuất.
```

## 8. Prompt debug

```text
Hãy chẩn đoán lỗi dưới đây trước, chưa sửa code ngay.

Hiện tượng:
[Mô tả chính xác]

Kỳ vọng:
[Hành vi đúng]

Cách tái hiện:
[Các bước/lệnh]

Output/log nguyên bản:
[Dán output đã loại secret]

Thay đổi gần nhất:
[Commit/PR/files]

Yêu cầu:
1. Xác định tầng lỗi: cloud, node, Kubernetes, network, application,
   database, telemetry hay test.
2. Liệt kê giả thuyết theo xác suất và bằng chứng cần thu thập.
3. Chạy kiểm tra read-only hẹp nhất trước.
4. Xác định root cause bằng evidence.
5. Đề xuất minimal fix và regression test.
6. Chỉ implement sau khi tôi đồng ý nếu fix làm thay đổi kiến trúc hoặc dữ liệu.
```

## 9. Prompt review PR/diff

```text
Hãy review thay đổi hiện tại so với default branch.

Ưu tiên theo thứ tự:
1. Correctness và hành vi sai.
2. Security, secret leakage và PSS restricted.
3. Data loss, migration, idempotency và failover risk.
4. Missing tests hoặc tests không chứng minh yêu cầu.
5. Observability gaps và high-cardinality telemetry.
6. Resource/cost risk.
7. Scope creep và tài liệu không khớp.

Với mỗi finding, cung cấp mức độ, file/vị trí, tác động, cách tái hiện hoặc
lập luận, và minimal fix. Không liệt kê style nit nếu không ảnh hưởng chất lượng.
Nếu không có finding, nêu rõ residual risks và checks đã xem.
```

## 10. Prompt kết thúc milestone

```text
Hãy đánh giá milestone [WEEK/MILESTONE] theo ROADMAP.md,
ACCEPTANCE_CRITERIA.md và DEFINITION_OF_DONE.md.

Không sửa code trong lượt đầu.

Hãy tạo bảng:
- Criterion ID.
- Trạng thái thực tế.
- Evidence hiện có.
- Evidence còn thiếu.
- Lệnh xác minh cần chạy.
- Blocker/risk.

Không đánh dấu Pass chỉ dựa trên việc file tồn tại. Cần runtime/test evidence.
Sau bảng, đề xuất thứ tự đóng các gap với effort và dependency.
```

## 11. Những prompt không nên dùng

Tránh:

```text
Hãy làm toàn bộ dự án cho tôi.
Hãy cài full observability tốt nhất.
Hãy sửa mọi lỗi và deploy production.
Hãy tối ưu toàn bộ repository.
```

Các prompt này không có phạm vi, điều kiện hoàn thành hoặc guardrail; dễ tạo code nhiều nhưng không kiểm chứng được.

## 12. Quy trình review của người thực hiện

Trước khi chấp nhận thay đổi do Codex tạo:

1. Đọc summary và lệnh kiểm tra.
2. Đọc toàn bộ diff, đặc biệt dependency, migration, workflow và security context.
3. Chạy lại lệnh quan trọng trên môi trường của mình.
4. Yêu cầu Codex giải thích phần không hiểu.
5. Đối chiếu acceptance IDs và evidence.
6. Chỉ merge khi bản thân có thể giải thích thay đổi với mentor.

