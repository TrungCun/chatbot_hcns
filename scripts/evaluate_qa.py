import asyncio
import csv
import logging
from typing import List, Dict, Any

from app.graph.builder import main_graph
from app.graph.state import create_initial_state
from app.model.llm import llm
from langchain_core.messages import HumanMessage
import uuid

# Setup an interceptor for logs to capture SQL and Rerank scores
class LogCaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.captured_logs = []

    def emit(self, record):
        msg = self.format(record)
        self.captured_logs.append(msg)

    def clear(self):
        self.captured_logs.clear()

logger = logging.getLogger()
log_capture = LogCaptureHandler()
logger.addHandler(log_capture)


QUESTIONS = [
    # 1. Chế độ Thử việc & Đào tạo
    "Cho mình hỏi thời gian thử việc ở công ty là bao lâu vậy ạ?",
    "Trong thời gian thử việc mình có được nhận 100% lương không, hay nhận 85% ạ?",
    "Thử việc bên mình có được đóng bảo hiểm (BHXH, BHYT) luôn không?",
    "Mới vào thì công ty có quy trình training (đào tạo) người mới không hay là vào làm việc luôn?",
    "Đánh giá đạt thử việc thì dựa trên những tiêu chí nào vậy ạ?",
    
    # 2. Lương, Thưởng & Phúc lợi
    "Công ty mình có lương tháng 13 không ạ?",
    "Bên mình review đánh giá tăng lương mấy lần 1 năm vậy?",
    "Ngoài lương cứng ra, công ty mình có phụ cấp ăn trưa, xăng xe hay gửi xe gì không?",
    "Vào các dịp Lễ, Tết (30/4, 2/9...) thì công ty có thưởng không? Mức thưởng thường là bao nhiêu ạ?",
    "Công ty có chế độ khám sức khỏe định kỳ hay bảo hiểm sức khỏe nào khác ngoài BHXH không?",
    "Cho mình hỏi các chế độ công đoàn như sinh nhật, ốm đau, hiếu hỉ bên mình quy định sao ạ?",

    # 3. Thời gian làm việc, Chấm công & OT
    "Thời gian làm việc bên mình là từ mấy giờ đến mấy giờ vậy? Có phải làm Thứ 7 không?",
    "Công ty mình chấm công bằng vân tay, quẹt thẻ hay chấm công qua app trên điện thoại thế ạ?",
    "Nếu đi muộn hoặc về sớm thì bị trừ lương như thế nào?",
    "Đặc thù công việc nếu phải ra ngoài gặp khách hàng thì chấm công kiểu gì vậy ạ?",
    "Nếu mình phải làm thêm giờ (OT) thì công ty tính lương OT như thế nào? Có quy trình đăng ký phức tạp không?",
    "Bên mình có cho phép làm remote (làm từ xa) hoặc thời gian linh hoạt (flexitime) không?",

    # 4. Chế độ Công tác
    "Vị trí này có hay phải đi công tác tỉnh không ạ?",
    "Công tác phí bên mình tính như thế nào? Tiền ăn ở, đi lại công ty lo trọn gói hay mình tự chi rồi về thanh toán?",
    "Trước khi đi công tác mình có được tạm ứng tiền trước không, hay phải tự bỏ tiền túi ra trước?",
    "Thủ tục hoàn ứng và thanh toán sau công tác có nhanh không ạ?",

    # 5. Môi trường, Văn hóa & Đồng phục
    "Công ty mình có bắt buộc mặc đồng phục cả tuần không hay được mặc đồ tự do ạ?",
    "Cho mình hỏi đồng phục công ty sẽ cấp phát hay nhân viên tự may/mua?",
    "Văn hóa công ty mình thế nào ạ? Mọi người có hay tổ chức team building hay du lịch công ty hàng năm không?",
    "Bên mình có quy tắc gì đặc biệt về trang phục hay tác phong làm việc không?",

    # 6. Giao việc & Đánh giá hiệu suất
    "Công ty mình quản lý công việc qua phần mềm nào (Jira, Trello, Base...) hay qua Zalo/Email ạ?",
    "KPI của vị trí này được đánh giá theo ngày, tuần hay tháng?",
    "Quy trình làm việc và giao việc giữa các phòng ban có rõ ràng không ạ?",

    # 7. Nghỉ phép & Nghỉ việc
    "Một năm mình được bao nhiêu ngày phép năm vậy ạ? Phép không nghỉ hết có được thanh toán tiền không?",
    "Nếu hết hạn hợp đồng hoặc muốn xin nghỉ việc thì mình phải báo trước bao nhiêu ngày?",

    # 8. Chuyên môn & Khác
    "Cho mình hỏi vị trí này phỏng vấn mấy vòng vậy ạ? Có bài test đầu vào không?",
    "Team Marketing hiện tại đang có bao nhiêu nhân sự vậy ạ?",
    "Sản phẩm/dịch vụ chủ lực hiện tại mang lại doanh thu chính cho AIPT Group là gì vậy?",

    # 9. Chit-chat (Kiểm tra xem bot có xử lý đúng không)
    "Bạn là bot hay là người thật đang chat với mình vậy?",
    "Chị HR bên mình có khó tính không bạn?"
]

async def evaluate_response_with_llm(question: str, response: str, documents: List[str]) -> tuple[str, str]:
    """Sử dụng LLM-as-a-judge để đánh giá câu trả lời dựa trên documents"""
    if not documents:
        return "N/A", "Không có tài liệu nào được sử dụng để trả lời (Có thể là chitchat hoặc fallback)."

    docs_text = "\n\n".join([f"Tài liệu {i+1}: {doc}" for i, doc in enumerate(documents)])
    
    prompt = f"""Bạn là một giám khảo đánh giá chất lượng hệ thống chatbot RAG.
Nhiệm vụ của bạn là kiểm tra xem câu trả lời của chatbot có hoàn toàn dựa trên các tài liệu đã truy xuất (retrieved documents) hay không.
Hãy đánh giá công tâm. Câu trả lời đúng phải:
1. Không bịaa đặt thông tin (hallucination).
2. Trả lời đúng trọng tâm câu hỏi dựa trên thông tin có trong tài liệu.

Câu hỏi từ người dùng:
{question}

Các tài liệu đã được chatbot truy xuất:
{docs_text}

Câu trả lời của chatbot:
{response}

Yêu cầu đầu ra:
Bạn phải đưa ra đánh giá của mình theo định dạng sau:
RESULT: [PASS hoặc FAIL]
REASON: [Giải thích ngắn gọn lý do tại sao PASS hoặc FAIL]

Ví dụ đầu ra:
RESULT: PASS
REASON: Câu trả lời cung cấp chính xác thông tin từ tài liệu 1 về thời gian thử việc.
"""
    try:
        msg = await llm.ainvoke([HumanMessage(content=prompt)])
        content = msg.content
        
        result = "FAIL"
        reason = content
        
        if "RESULT: PASS" in content.upper():
            result = "PASS"
        elif "RESULT: FAIL" in content.upper():
            result = "FAIL"
            
        return result, reason
    except Exception as e:
        return "ERROR", str(e)


async def run_evaluation():
    from app.application import application
    print("Đang tải các models...")
    application.load_models()
    
    results = []
    
    print(f"Bắt đầu đánh giá {len(QUESTIONS)} câu hỏi...")
    
    for i, question in enumerate(QUESTIONS):
        print(f"\n--- Đang xử lý câu {i+1}/{len(QUESTIONS)}: {question} ---")
        
        session_id = str(uuid.uuid4())
        user_id = "test_user_eval"
        
        state = create_initial_state(
            message=question,
            session_id=session_id,
            user_id=user_id,
        )
        
        config = {"configurable": {"thread_id": f"{user_id}_{session_id}"}}
        
        log_capture.clear()
        
        try:
            # Chạy qua LangGraph bằng astream_events để bắt được các biến nội bộ (domain, retrieved_documents)
            response = "Không có câu trả lời"
            domain = "unknown"
            retrieved_docs = []
            
            async for event in main_graph.astream_events(state, config, version="v2"):
                if event.get("event") == "on_chain_end":
                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict):
                        if "domain" in output:
                            domain = output["domain"]
                        if "retrieved_documents" in output:
                            retrieved_docs = output["retrieved_documents"]
                        if "response" in output:
                            response = output["response"]
            
            # Lọc các log quan trọng (SQL, Rerank scores)
            debug_logs = []
            for log_msg in log_capture.captured_logs:
                if "[handle_job_query] generated SQL" in log_msg:
                    debug_logs.append(log_msg)
                elif "[rerank_documents]" in log_msg and "[Score:" in log_msg:
                    debug_logs.append(log_msg)
            
            debug_info_str = "\n".join(debug_logs)
            
            # Đánh giá bằng LLM nếu domain thuộc về company hoặc job (có dùng tài liệu)
            eval_result = "N/A"
            eval_reason = "Không đánh giá"
            
            if domain in ["company", "job"] and retrieved_docs:
                eval_result, eval_reason = await evaluate_response_with_llm(question, response, retrieved_docs)
            elif domain == "chitchat":
                eval_reason = "Bỏ qua đánh giá tài liệu vì đây là nhánh Chit-chat."
            elif not retrieved_docs:
                 eval_reason = "Không có tài liệu nào được trả về (Fallback)."
                 
            results.append({
                "STT": i + 1,
                "Chủ đề / Nhánh": domain,
                "Câu hỏi": question,
                "Câu trả lời": response,
                "Số lượng tài liệu": len(retrieved_docs),
                "Kết quả (PASS/FAIL)": eval_result,
                "Lý do đánh giá": eval_reason,
                "Debug Logs (SQL/Rerank)": debug_info_str
            })
            
            print(f"Hoàn thành câu {i+1}. Kết quả: {eval_result}")
            
        except Exception as e:
            print(f"Lỗi khi xử lý câu hỏi '{question}': {e}")
            results.append({
                "STT": i + 1,
                "Chủ đề / Nhánh": "error",
                "Câu hỏi": question,
                "Câu trả lời": f"Lỗi: {e}",
                "Số lượng tài liệu": 0,
                "Kết quả (PASS/FAIL)": "ERROR",
                "Lý do đánh giá": "Có lỗi hệ thống",
                "Debug Logs (SQL/Rerank)": ""
            })

    # Lưu kết quả ra file CSV
    output_file = "qa_evaluation_report.csv"
    if results:
        fieldnames = ["STT", "Chủ đề / Nhánh", "Câu hỏi", "Câu trả lời", "Số lượng tài liệu", "Kết quả (PASS/FAIL)", "Lý do đánh giá", "Debug Logs (SQL/Rerank)"]
        with open(output_file, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        print(f"\n✅ Đã xuất báo cáo ra file: {output_file}")
    else:
        print("\nKhông có kết quả nào được lưu.")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
