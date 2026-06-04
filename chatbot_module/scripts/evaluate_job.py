import asyncio
import csv
import logging
import re
from typing import List

import os
import sys

# Add project root to sys.path so 'app' can be imported
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from app.graph.builder import main_graph
from app.graph.state import create_initial_state
from app.model.llm import llm
from langchain_core.messages import HumanMessage
import uuid

# Setup an interceptor for logs to capture SQL
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

def load_questions_from_md(file_path: str) -> List[str]:
    questions = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                # Tìm các dòng có định dạng "1. Câu hỏi...", "2. Câu hỏi..."
                match = re.match(r'^\d+\.\s*(.+)', line.strip())
                if match:
                    questions.append(match.group(1))
    except Exception as e:
        print(f"Lỗi khi đọc file markdown: {e}")
    return questions

async def evaluate_job_response_with_llm(question: str, response: str, debug_logs: str) -> tuple[str, str]:
    """Sử dụng LLM-as-a-judge để đánh giá câu lệnh SQL và câu trả lời"""
    prompt = f"""Bạn là một chuyên gia đánh giá chất lượng hệ thống AI (LLM-as-a-judge).
Nhiệm vụ của bạn là kiểm tra xem AI có xử lý đúng yêu cầu tìm kiếm việc làm hay không.
Hãy xem xét câu lệnh SQL đã sinh ra có đúng với ý định người dùng không và câu trả lời có phản ánh hợp lý kết quả không.

Câu hỏi từ người dùng:
{question}

Thông tin Debug (chứa câu lệnh SQL đã được sinh ra, nếu có):
{debug_logs}

Câu trả lời của chatbot:
{response}

Yêu cầu đầu ra:
Bạn phải đưa ra đánh giá của mình theo định dạng sau:
RESULT: [PASS hoặc FAIL]
REASON: [Giải thích ngắn gọn lý do tại sao PASS hoặc FAIL. Hãy phân tích xem SQL có đáp ứng đúng điều kiện tìm kiếm không, hoặc AI có trả lời hợp lý không]

Ví dụ đầu ra:
RESULT: PASS
REASON: Câu lệnh SQL đã sử dụng đúng LIKE '%15%' hoặc các điều kiện hợp lý cho mức lương. Chatbot phản hồi đúng thông tin.
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
    from app.tools.mysql import init_mysql, close_mysql
    
    print("Đang tải các models...")
    application.load_models()
    
    print("Khởi tạo kết nối MySQL...")
    init_mysql()
    
    try:
        questions = load_questions_from_md("scripts/job_questions.md")
        if not questions:
            print("Không tìm thấy câu hỏi nào trong scripts/job_questions.md")
            return
    
        results = []
        
        print(f"Bắt đầu đánh giá {len(questions)} câu hỏi về việc làm...")
        
        for i, question in enumerate(questions):
            print(f"\n--- Đang xử lý câu {i+1}/{len(questions)}: {question} ---")
            
            session_id = str(uuid.uuid4())
            user_id = "test_user_eval_job"
            
            state = create_initial_state(
                message=question,
                session_id=session_id,
                user_id=user_id,
            )
            
            config = {"configurable": {"thread_id": f"{user_id}_{session_id}"}}
            
            log_capture.clear()
            
            try:
                response = "Không có câu trả lời"
                domain = "unknown"
                
                async for event in main_graph.astream_events(state, config, version="v2"):
                    if event.get("event") == "on_chain_end":
                        output = event.get("data", {}).get("output")
                        if isinstance(output, dict):
                            if "domain" in output:
                                domain = output["domain"]
                            if "response" in output:
                                response = output["response"]
                
                # Lọc các log quan trọng (SQL)
                debug_logs = []
                for log_msg in log_capture.captured_logs:
                    if "[handle_job_query] generated SQL" in log_msg:
                        debug_logs.append(log_msg)
                    elif "[check_jobs] executing query" in log_msg:
                        debug_logs.append(log_msg)
                
                debug_info_str = "\n".join(debug_logs)
                
                # Đánh giá bằng LLM nếu domain là job
                eval_result = "N/A"
                eval_reason = "Không đánh giá"
                
                if domain == "job":
                    eval_result, eval_reason = await evaluate_job_response_with_llm(question, response, debug_info_str)
                else:
                    eval_reason = f"Không thuộc nhánh job (Nhánh hiện tại: {domain}). Đánh giá FAIL."
                    eval_result = "FAIL"
                     
                results.append({
                    "STT": i + 1,
                    "Chủ đề / Nhánh": domain,
                    "Câu hỏi": question,
                    "Câu trả lời": response,
                    "Kết quả (PASS/FAIL)": eval_result,
                    "Lý do đánh giá": eval_reason,
                    "Debug Logs (SQL)": debug_info_str
                })
                
                print(f"Hoàn thành câu {i+1}. Kết quả: {eval_result}")
                
            except Exception as e:
                print(f"Lỗi khi xử lý câu hỏi '{question}': {e}")
                results.append({
                    "STT": i + 1,
                    "Chủ đề / Nhánh": "error",
                    "Câu hỏi": question,
                    "Câu trả lời": f"Lỗi: {e}",
                    "Kết quả (PASS/FAIL)": "ERROR",
                    "Lý do đánh giá": "Có lỗi hệ thống",
                    "Debug Logs (SQL)": ""
                })
    
        # Lưu kết quả ra file CSV
        output_file = "job_evaluation_report.csv"
        if results:
            fieldnames = ["STT", "Chủ đề / Nhánh", "Câu hỏi", "Câu trả lời", "Kết quả (PASS/FAIL)", "Lý do đánh giá", "Debug Logs (SQL)"]
            with open(output_file, mode="w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in results:
                    writer.writerow(row)
            print(f"\n✅ Đã xuất báo cáo ra file: {output_file}")
        else:
            print("\nKhông có kết quả nào được lưu.")
            
    finally:
        print("Đóng kết nối MySQL...")
        close_mysql()

if __name__ == "__main__":
    asyncio.run(run_evaluation())
