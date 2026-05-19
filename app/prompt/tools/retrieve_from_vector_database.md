<tool_description>
Bạn **MUST** sử dụng tool này để truy xuất tài liệu phi cấu trúc (unstructured documents) từ Cơ sở dữ liệu Vector (Vector Database). Dữ liệu này bao gồm toàn bộ kho tri thức nội bộ, quy định, và chính sách Hành chính Nhân sự (HCNS) của công ty.
</tool_description>

<trigger_conditions>
**IF** câu hỏi của người dùng thuộc các chủ đề sau, **THEN** bạn **MUST** gọi tool này:
- Quy định, nội quy công ty (ví dụ: giờ làm việc, quy định chấm công, xin nghỉ phép, quy tắc ứng xử).
- Chính sách và đãi ngộ (ví dụ: cơ cấu lương, thưởng lễ tết, bảo hiểm, trợ cấp, phúc lợi).
- Tài liệu hội nhập (onboarding), lộ trình thăng tiến, quy trình đào tạo nội bộ.
- Các quy trình hành chính (ví dụ: thanh toán công tác phí, cấp phát thiết bị).
</trigger_conditions>

<constraints>
1. TRÁNH XUNG ĐỘT (DISAMBIGUATION): Bạn **MUST NOT** sử dụng tool này **IF** người dùng hỏi về "các vị trí đang tuyển", "cơ hội việc làm mới". (Đối với các trường hợp đó, hệ thống có định tuyến riêng).
2. PHẠM VI (SCOPE OVERRIDE): Tool này **ONLY** chứa dữ liệu nội bộ công ty. Bạn **NEVER** được gọi tool này cho các câu hỏi về kiến thức chung bên ngoài.
</constraints>

<parameter_definitions>
1. `prompt` (string, required): 
   - Đây là chuỗi truy vấn (search query) sẽ được dùng để thực hiện Semantic Search.
   - Trạng thái đầu vào đã được hệ thống tiền xử lý và làm giàu. Do đó, bạn **MUST** truyền nguyên văn (exact match) câu hỏi từ ngữ cảnh vào tham số này. 
   - Bạn **MUST NOT** tự ý sửa đổi, viết lại, **OR** tóm tắt lại chuỗi truy vấn này.

2. `limit` (integer, optional): 
   - Số lượng tài liệu (chunks) tối đa trả về. Mặc định là 5.
   - Bạn **SHOULD** thiết lập `limit = 7` hoặc `limit = 10` **IF** câu hỏi mang tính chất tổng hợp, đòi hỏi đối chiếu nhiều nguồn chính sách khác nhau (ví dụ: so sánh các chế độ).
</parameter_definitions>