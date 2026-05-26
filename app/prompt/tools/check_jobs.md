<tool_description>
Bạn **MUST** sử dụng tool này để truy vấn thông tin tuyển dụng từ cơ sở dữ liệu MySQL bằng cách truyền vào một câu lệnh SQL **SELECT** phù hợp với câu hỏi của người dùng.
</tool_description>

<trigger_conditions>
**IF** câu hỏi của người dùng liên quan đến thông tin tuyển dụng như: vị trí ứng tuyển, yêu cầu công việc, câu hỏi phỏng vấn, trạng thái đơn ứng tuyển, hoặc bất kỳ dữ liệu nào cần truy xuất từ hệ thống tuyển dụng, **THEN** bạn **MUST** kích hoạt tool này.
</trigger_conditions>

<input_definition>

- **query** (string, bắt buộc): Câu lệnh SQL **SELECT** được tạo ra dựa trên câu hỏi của người dùng. Chỉ cho phép câu lệnh **SELECT**, không được dùng INSERT, UPDATE, DELETE, DROP hoặc bất kỳ lệnh thay đổi dữ liệu nào.
  </input_definition>

<returns_definition>

- **RETURNS**: Danh sách các bản ghi (list of dict) trả về từ kết quả truy vấn SQL.
- **IF** không có dữ liệu phù hợp, **THEN** tool **WILL RETURN** thông báo không tìm thấy kết quả.
- **IF** câu lệnh SQL bị lỗi, **THEN** tool **WILL RETURN** thông báo lỗi chi tiết.
  </returns_definition>
