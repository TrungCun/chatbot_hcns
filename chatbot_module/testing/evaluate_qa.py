import asyncio
import csv
import logging
import time
import os
import sys
import re
from typing import List, Dict, Any

# Add project root to sys.path so 'app' can be imported
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from bot_app.graph.builder import main_graph
from bot_app.graph.state import create_initial_state
from bot_app.model.llm import llm
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
    from bot_app.application import application
    print("Đang tải các models...")
    application.load_models()
    
    base_dir = os.path.dirname(__file__)
    md_path = os.path.join(base_dir, "qa_test_bank.md")
    questions = load_questions_from_md(md_path)
    if not questions:
        print(f"Không tìm thấy câu hỏi nào trong {md_path}")
        return
        
    results = []
    
    print(f"Bắt đầu đánh giá {len(questions)} câu hỏi...")
    
    for i, question in enumerate(questions):
        print(f"\n--- Đang xử lý câu {i+1}/{len(questions)}: {question} ---")
        
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
            
            start_time = time.time()
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
            
            end_time = time.time()
            response_time = end_time - start_time
            
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
                "Thời gian trả lời (s)": round(response_time, 2),
                "Kết quả (PASS/FAIL)": eval_result,
                "Lý do đánh giá": eval_reason,
                "Debug Logs (SQL/Rerank)": debug_info_str
            })
            
            print(f"Hoàn thành câu {i+1}. Kết quả: {eval_result} | Thời gian: {response_time:.2f}s")
            
        except Exception as e:
            print(f"Lỗi khi xử lý câu hỏi '{question}': {e}")
            results.append({
                "STT": i + 1,
                "Chủ đề / Nhánh": "error",
                "Câu hỏi": question,
                "Câu trả lời": f"Lỗi: {e}",
                "Số lượng tài liệu": 0,
                "Thời gian trả lời (s)": 0,
                "Kết quả (PASS/FAIL)": "ERROR",
                "Lý do đánh giá": "Có lỗi hệ thống",
                "Debug Logs (SQL/Rerank)": ""
            })

    # Tính toán thống kê
    total_questions = len(results)
    pass_count = sum(1 for r in results if r["Kết quả (PASS/FAIL)"] == "PASS")
    fail_count = sum(1 for r in results if r["Kết quả (PASS/FAIL)"] == "FAIL")
    error_count = sum(1 for r in results if r["Kết quả (PASS/FAIL)"] == "ERROR")
    
    accuracy = (pass_count / total_questions) * 100 if total_questions > 0 else 0
    
    valid_times = [r["Thời gian trả lời (s)"] for r in results if r.get("Thời gian trả lời (s)", 0) > 0]
    avg_time = sum(valid_times) / len(valid_times) if valid_times else 0
    max_time = max(valid_times) if valid_times else 0
    min_time = min(valid_times) if valid_times else 0

    print("\n" + "="*50)
    print("BÁO CÁO THỐNG KÊ ĐÁNH GIÁ (QA)")
    print("="*50)
    print(f"Tổng số câu hỏi       : {total_questions}")
    print(f"Số câu PASS           : {pass_count}")
    print(f"Số câu FAIL           : {fail_count}")
    print(f"Số câu LỖI            : {error_count}")
    print(f"Độ chính xác (PASS)   : {accuracy:.2f}%")
    print(f"Thời gian TB          : {avg_time:.2f}s")
    print(f"Thời gian Min         : {min_time:.2f}s")
    print(f"Thời gian Max         : {max_time:.2f}s")
    print("="*50)

    # Lưu kết quả ra file CSV
    output_file = "qa_evaluation_report.csv"
    if results:
        fieldnames = ["STT", "Chủ đề / Nhánh", "Câu hỏi", "Câu trả lời", "Số lượng tài liệu", "Thời gian trả lời (s)", "Kết quả (PASS/FAIL)", "Lý do đánh giá", "Debug Logs (SQL/Rerank)"]
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
