# Báo cáo Phân tích Stress Test Multi-turn & Accuracy (62 lượt)

_Đây là báo cáo tổng hợp quá trình chạy kịch bản 62 câu hỏi liên tục trên duy nhất một session để kiểm thử độ chịu tải, khả năng duy trì ngữ cảnh (Memory) và độ chính xác của LLM Chatbot HCNS._

## 1. Kết quả Độ Chính Xác (Accuracy Report)

Hệ thống giám khảo LLM-as-a-judge đã phân tích từng câu hỏi và nhận xét trực tiếp quá trình bot phản hồi (kết hợp với lịch sử Chat).

- **Tổng số câu hỏi chạy liên hoàn:** 62 câu
- **Số câu Hợp lệ để đánh giá (Domain Job/QA):** 47 câu
- **Số câu Bỏ qua (Chitchat):** 15 câu (N/A)
- **Đánh giá Đạt (PASS):** 44 câu
- **Đánh giá Trượt (FAIL):** 3 câu

**Độ Chính Xác Tổng Thể (Trừ N/A): 93.62%**

Đây là một con số rất ấn tượng với kịch bản chạy nhồi nhét multi-turn, chứng tỏ bot không hề bị "ảo giác" nặng hay "lạc đề" khi bối cảnh hội thoại ngày càng dài ra.

## 2. Báo cáo Thời gian Trung bình (Response Time)

Khả năng phản hồi của hệ thống được duy trì rất ổn định bất chấp việc phải chạy thêm tác vụ Update Context ở mỗi turn. Trung bình toàn kịch bản là **5.59 giây / lượt**:

- **Tán gẫu (Chit-chat):** `~1.92 s` _(Rất nhanh do không phải gọi CSDL hay Vector Search)_
- **Hỏi đáp Công ty/Chính sách (RAG):** `~4.39 s` _(Tốc độ Retrieve qua Qdrant và sinh câu trả lời ấn tượng)_
- **Hỏi đáp Việc làm (Text-to-SQL):** `~7.92 s` _(Lâu nhất do phải qua nhiều bước LLM: Gen SQL -> Run DB -> Sinh câu trả lời)_

## 3. Phân tích 3 Câu bị đánh giá FAIL

Trong tổng số 47 câu nghiệp vụ, hệ thống trọng tài LLM-as-a-judge đã soi ra 3 câu bị lỗi nghiệp vụ. Các lỗi này thiên về Prompt Engineering:

**Turn 6: "Công ty mình có lương tháng 13 không ạ?" (Domain: Company)**

- **Lý do FAIL:** Lỗi Hallucination (Bịa đặt). Bot tự động thêm chữ "công ty AIPT" vào câu trả lời, trong khi tài liệu RAG trích xuất ra ở turn đó chỉ nói chung chung về chính sách chứ không hề đề cập đến tên công ty "AIPT".
- **Gợi ý fix:** Thêm nhắc nhở vào prompt sinh câu trả lời RAG: _"Tuyệt đối không tự bịa thêm tên công ty nếu tài liệu không đề cập"_.

**Turn 13: "Công ty mình chấm công bằng vân tay, quẹt thẻ hay chấm công qua app trên điện thoại thế ạ?" (Domain: Company)**

- **Lý do FAIL:** Không sử dụng thông tin RAG cung cấp. Tài liệu RAG trích xuất có ghi rõ nhân viên tại văn phòng "chấm vân tay bằng máy chấm công". Tuy nhiên, bot lại trả lời là _"Tài liệu hiện tại không đề cập đến việc chấm công bằng vân tay"_.
- **Gợi ý fix:** Cần tối ưu lại `validate_retrieval` hoặc Prompt `generate_response` để bot chịu khó đọc kỹ chunk hơn.

**Turn 37: "Có vị trí nào đòi hỏi kinh nghiệm 3 năm trở lên không?" (Domain: Job)**

- **Lý do FAIL:** Bot trả lời _"Tất cả các vị trí đang mở tại AIPT đều yêu cầu mức kinh nghiệm là 3 năm"_ và liệt kê một danh sách dài. Trọng tài cho rằng câu trả lời này "quá tuyệt đối" và có biểu hiện của việc lấy toàn bộ danh sách công việc mà quên mất bộ lọc SQL `WHERE experience >= 3`.
- **Gợi ý fix:** Nhánh text-to-sql cần sinh câu trả lời bám sát dữ liệu SQL hơn, thay vì dùng từ "tất cả", bot nên dùng "Dưới đây là các vị trí yêu cầu trên 3 năm...".

## 4. Kiểm chứng Độ ổn định Hệ thống

- **Context Manager**: Sau 62 câu, bộ nhớ `KEEP_COUNT = 8` vẫn chạy mượt mà, tóm tắt chính xác ngữ cảnh. Không xảy ra tràn RAM (Memory Leak).
- **GPU Usage**: Dung lượng VRAM trên card 1 luôn giữ ổn định ở mức `~17GB` trong suốt lúc chạy cả 3 luồng LLM cùng lúc (Trả lời + Nén ngữ cảnh + Giám khảo LLM).
