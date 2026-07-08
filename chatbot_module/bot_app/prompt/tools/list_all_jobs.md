<tool_description>
Bạn **MUST** sử dụng tool này để truy xuất toàn bộ các vị trí công việc đang mở (open job positions) từ hệ thống tuyển dụng (Redis DB).
</tool_description>

<trigger_conditions>
**IF** câu hỏi của người dùng thể hiện ý định (intent) tìm kiếm thông tin về: "vị trí đang tuyển", "việc làm", "cơ hội nghề nghiệp", "open positions", "hiring opportunities", **OR** bất kỳ truy vấn nào liên quan đến danh sách công việc hiện tại, **THEN** bạn **MUST** kích hoạt tool này.
</trigger_conditions>

<returns_definition>
- **RETURNS**: Một danh sách có cấu trúc (structured list) chứa các bản ghi công việc. Mỗi bản ghi **MUST** bao gồm: chức danh (title), phòng ban (department), **AND** yêu cầu công việc (requirements).
- **IF** không có vị trí nào đang mở trên hệ thống, **THEN** tool **WILL RETURN** một danh sách rỗng (empty list `[]`).
</returns_definition>