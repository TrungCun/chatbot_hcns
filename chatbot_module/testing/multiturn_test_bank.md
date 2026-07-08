# Ngân Hàng Câu Hỏi Multi-turn (Stress Test)

File này chứa các kịch bản kiểm thử hội thoại nhiều lượt (multi-turn). 
Mỗi tiêu đề (Header bắt đầu bằng `#`) là một kịch bản, đại diện cho một phiên làm việc (session) riêng biệt. 
Các câu hỏi bên dưới sẽ được chạy nối tiếp nhau để kiểm tra khả năng bám sát ngữ cảnh của bot.

## Kịch bản 1: Đổi chủ đề liên tục (Chính sách -> Chit-chat -> Việc làm)
1. Quy định về việc làm thêm giờ (OT) của công ty như thế nào?
2. Chà, chính sách cũng khá ổn đấy. Bạn ăn trưa chưa bot?
3. Sẵn tiện cho mình hỏi công ty có đang tuyển dụng lập trình viên Backend không?
4. Mức lương cho vị trí vừa rồi là bao nhiêu?

## Kịch bản 2: Tìm việc tăng dần điều kiện (Incremental Search)
1. Mình muốn tìm công việc liên quan đến Marketing.
2. Mình muốn vị trí nào không yêu cầu kinh nghiệm (fresher) thôi nhé.
3. Trong các vị trí đó, có việc nào ở Hà Nội không?
4. Cho mình xem mô tả công việc của vị trí đầu tiên nhé.

## Kịch bản 3: Hỏi sâu về chính sách
1. Cho mình hỏi thủ tục nghỉ việc cần phải làm những gì?
2. Nếu mình chỉ là nhân viên thử việc thì có cần báo trước không?
3. Báo trước bao nhiêu ngày vậy?
4. Tiền lương những ngày chưa thanh toán sẽ được nhận như thế nào?
