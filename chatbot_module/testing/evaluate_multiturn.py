import os
import sys
import uuid
import time
import asyncio
import pandas as pd
from dotenv import load_dotenv

# Thêm thư mục root vào sys.path để import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from bot_app.config import settings
os.environ["CUDA_VISIBLE_DEVICES"] = str(settings.gpu_device)

from bot_app.graph.builder import main_graph
from bot_app.graph.state import create_initial_state
from bot_app.tools.mysql import init_mysql, close_mysql
from testing.evaluate_qa import load_questions_from_md, evaluate_response_with_llm
from testing.evaluate_job import evaluate_job_response_with_llm
from bot_app.application import application

async def run_stress_test():
    base_dir = os.path.dirname(__file__)
    md_path = os.path.join(base_dir, "regression_test_bank.md")
    
    questions = load_questions_from_md(md_path)
    if not questions:
        print(f"Không tìm thấy câu hỏi nào trong {md_path}")
        return
        
    print("Đang khởi tạo kết nối Database & load Models...")
    init_mysql()
    try:
        application.load_models()
    except Exception as e:
        print(f"Lỗi load model: {e}")
        
    results = []
    
    print(f"Bắt đầu STRESS TEST: Đưa {len(questions)} câu hỏi vào chung MỘT (1) session duy nhất...")
    print("="*50)
    
    # CHỈ TẠO 1 SESSION DUY NHẤT
    session_id = str(uuid.uuid4())
    user_id = "test_user_stresstest"
    config = {"configurable": {"thread_id": f"{user_id}_{session_id}"}}
    
    for q_idx, question in enumerate(questions):
        print(f"\n--- [Turn {q_idx+1}/{len(questions)}] User: {question} ---")
        
        # --- Lấy State Cũ ---
        previous_state_values = None
        try:
            previous_state = main_graph.get_state(config)
            if previous_state and previous_state.values:
                previous_state_values = previous_state.values
        except Exception as e:
            pass
            
        state = create_initial_state(
            message=question,
            session_id=session_id,
            user_id=user_id,
            previous_state=previous_state_values
        )
        
        # --- Chạy Graph ---
        response_text = "Không có câu trả lời"
        domain = "unknown"
        retrieved_docs = []
        debug_info_str = ""
        
        start_time = time.time()
        async for event in main_graph.astream_events(state, config, version="v2"):
            if event.get("event") == "on_chain_end":
                output = event.get("data", {}).get("output")
                if isinstance(output, dict):
                    if "domain" in output:
                        domain = output["domain"]
                    if "response" in output:
                        response_text = output["response"]
                    if "retrieved_documents" in output:
                        retrieved_docs = output["retrieved_documents"]
                    if "debug_info" in output:
                        debug_info_str = output["debug_info"]
                        
        end_time = time.time()
        duration = end_time - start_time
        
        # 🚀 KÍCH HOẠT UPDATE CONTEXT NGẦM (Nén history) 🚀
        await main_graph.ainvoke(None, config)
        
        # Lấy context MỚI sau khi đã nén
        current_state = main_graph.get_state(config)
        context_saved = current_state.values.get("context", "Chưa có bối cảnh") if current_state and current_state.values else "N/A"
        history_len = len(current_state.values.get("history", [])) if current_state and current_state.values else 0
        
        # --- Đánh giá Accuracy ---
        eval_result = "N/A"
        eval_reason = ""
        if domain in ["company", "policy"]:
            if retrieved_docs:
                eval_result, eval_reason = await evaluate_response_with_llm(question, response_text, retrieved_docs)
            else:
                eval_reason = "Không tìm thấy tài liệu (Fallback)"
        elif domain == "job":
            eval_result, eval_reason = await evaluate_job_response_with_llm(question, response_text, debug_info_str)
        elif domain == "chitchat":
            eval_reason = "Chit-chat (Bỏ qua)"
        
        print(f"Bot [{domain}] ({duration:.2f}s): {response_text[:100]}...")
        print(f"[Memory - Dài {history_len} msgs]: {context_saved}")
        print(f"[Đánh giá]: {eval_result} | Lý do: {eval_reason}")
        
        results.append({
            "Turn": q_idx + 1,
            "Domain": domain,
            "Question": question,
            "Response": response_text,
            "Result": eval_result,
            "Reason": eval_reason,
            "History Length": history_len,
            "Context Used": context_saved,
            "Time (s)": round(duration, 2)
        })
            
    # Xuất báo cáo
    df = pd.DataFrame(results)
    output_file = "regression_test_report.csv"
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    
    # Tính toán báo cáo
    total_q = len(results)
    pass_q = len([r for r in results if r["Result"] == "PASS"])
    fail_q = len([r for r in results if r["Result"] == "FAIL"])
    na_q = len([r for r in results if r["Result"] == "N/A"])
    evaluated_q = pass_q + fail_q
    accuracy = (pass_q / evaluated_q * 100) if evaluated_q > 0 else 0
    
    print("\n" + "="*50)
    print("HOÀN THÀNH STRESS TEST MULTI-TURN 62 CÂU HỎI")
    print(f"Tổng số câu: {total_q}")
    print(f"PASS: {pass_q} | FAIL: {fail_q} | N/A: {na_q}")
    print(f"ĐỘ CHÍNH XÁC (Trừ N/A): {accuracy:.2f}%")
    print(f"Đã xuất chi tiết ra file: {output_file}")
    print("="*50)
    
    close_mysql()
    application.cleanup_models()

if __name__ == "__main__":
    asyncio.run(run_stress_test())
